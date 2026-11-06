"""Small standard-library HTTP server for the MVP."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import date
import json, os, re
from . import store
ROOT=Path(__file__).resolve().parent
def build_version():
    v=os.environ.get("CLIENT_CONFIG_BUILD_VERSION") or os.environ.get("BUILD_VERSION")
    if v: return v
    try:
        import subprocess
        # Exact reviewed checkout provenance: prefer commit SHA over branch name.
        out=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT.parent,text=True,stderr=subprocess.DEVNULL).strip()
        if out: return out
    except Exception:
        pass
    try:
        import subprocess
        out=subprocess.check_output(["git","rev-parse","--abbrev-ref","HEAD"],cwd=ROOT.parent,text=True,stderr=subprocess.DEVNULL).strip()
        if out and out!="HEAD": return out
    except Exception:
        pass
    return "unknown"
class Handler(BaseHTTPRequestHandler):
    def send_json(self,data,status=200,headers=None):
        if status>=400:self.log_message("API response status=%s path=%s",status,urlparse(self.path).path)
        raw=json.dumps(data,ensure_ascii=False).encode(); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(raw))); self.send_header("Cache-Control","no-store")
        for k,v in (headers or {}).items():self.send_header(k,v)
        self.end_headers(); self.wfile.write(raw)
    def body(self):
        size=int(self.headers.get("Content-Length",0)); return json.loads(self.rfile.read(size) or b"{}")
    def do_GET(self):
        parsed=urlparse(self.path); path=parsed.path; q=parse_qs(parsed.query)
        try:
            if path=="/api/health":return self.send_json({"status":"ok","service":"client-config-mvp"})
            if path=="/api/v1/build-info":return self.send_json({"build_id":build_version()})
            if path=="/api/v1/discovery":return self.send_json({"catalog":store.discovery_catalog(),"decisions":store.discovery_decisions()})
            if path=="/api/v1/config-schemas":return self.send_json(store.configuration_schemas())
            schema_match=re.fullmatch(r"/api/v1/config-schemas/(\d+)",path)
            if schema_match:
                version=schema_match.group(1); record=store.configuration_schema(version)
                schema=record["schema"]
                return self.send_json({"version":version,"schema":schema,"effective_from":record["effective_from"],"recorded_at":record["recorded_at"],"parameters":store.config_schema.parameter_definitions(schema)})
            if path=="/favicon.ico":
                self.send_response(204); self.end_headers(); return
            if path=="/api/customers":return self.send_json(store.customers())
            temporal_history=re.fullmatch(r"/api/customers/([\w-]+)/history",path)
            if temporal_history:
                history=store.config_knowledge_history(temporal_history.group(1))
                return self.send_json(history) if history else self.send_json({"error":"not_found"},404)
            if path=="/api/changes":return self.send_json(store.list_changes())
            if path=="/api/profiles":return self.send_json(store.profiles())
            if path=="/api/audit":return self.send_json(store.audit_log())
            if path=="/api/policies":return self.send_json(store.policies())
            if path=="/api/v1/policies":
                valid_at=q.get("valid_at",[None])[0]; known_at=q.get("known_at",[None])[0]
                if not valid_at or not known_at:return self.send_json({"error":"valid_at en known_at zijn verplicht"},400)
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",valid_at):return self.send_json({"error":"valid_at moet ISO-formaat YYYY-MM-DD hebben"},400)
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|\+00:00)?",known_at):return self.send_json({"error":"known_at moet UTC ISO 8601 zijn"},400)
                try: date.fromisoformat(valid_at); store._utc_stamp(known_at)
                except ValueError:return self.send_json({"error":"Ongeldig datum- of tijdformaat"},400)
                return self.send_json(store.policies_as_of(valid_at,known_at))
            if path=="/api/client-requirements":return self.send_json(store.client_requirements(q.get("customer_id",[None])[0],q.get("valid_at",[None])[0],q.get("known_at",[None])[0]))
            requirement_time_query=re.fullmatch(r"/api/v1/customers/([\w-]+)/client-requirements",path)
            if requirement_time_query:
                customer_id=requirement_time_query.group(1)
                valid_at=q.get("valid_at",[None])[0]; known_at=q.get("known_at",[None])[0]
                if not valid_at or not known_at:return self.send_json({"error":"valid_at en known_at zijn verplicht"},400)
                if not store.customer(customer_id):return self.send_json({"error":"not_found"},404)
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",valid_at):return self.send_json({"error":"valid_at moet ISO-formaat YYYY-MM-DD hebben"},400)
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|\+00:00)?",known_at):
                    return self.send_json({"error":"known_at moet een UTC ISO 8601-tijd zijn"},400)
                try:
                    date.fromisoformat(valid_at); store._utc_stamp(known_at)
                except ValueError:return self.send_json({"error":"Ongeldig datum- of tijdformaat"},400)
                return self.send_json(store.client_requirements(customer_id,valid_at,known_at))
            register_history=re.fullmatch(r"/api/v1/customers/([\w-]+)/register-history",path)
            if register_history:
                history=store.graph_knowledge_history(register_history.group(1))
                return self.send_json(history) if history else self.send_json({"error":"not_found"},404)
            if path=="/api/dora-assessments":return self.send_json(store.dora_assessments())
            if path=="/api/chain-parties":return self.send_json(store.chain_parties(customer_id=q.get("customer_id",[None])[0]))
            if path=="/api/v1/chain-parties":
                valid_at=q.get("valid_at",[None])[0]; known_at=q.get("known_at",[None])[0]
                if not valid_at or not known_at:return self.send_json({"error":"valid_at en known_at zijn verplicht"},400)
                try: date.fromisoformat(valid_at); store._utc_stamp(known_at)
                except ValueError:return self.send_json({"error":"Ongeldig datum- of tijdformaat"},400)
                cid=q.get("customer_id",[None])[0]
                if not cid:return self.send_json({"error":"customer_id is verplicht"},400)
                return self.send_json(store.chain_parties(customer_id=cid,valid_at=valid_at,known_at=known_at))
            chain_trace=re.fullmatch(r"/api/customers/([\w-]+)/chain-trace/([\w-]+)",path)
            if chain_trace:
                try: trace=store.chain_trace(customer_id=chain_trace.group(1),party_id=chain_trace.group(2),valid_at=q.get("valid_at",[None])[0],known_at=q.get("known_at",[None])[0])
                except ValueError as e: return self.send_json({"error":str(e)},404)
                return self.send_json(trace)
            chain_impact=re.fullmatch(r"/api/customers/([\w-]+)/chain-impact/([\w-]+)",path)
            if chain_impact:
                try: impact=store.chain_impact(customer_id=chain_impact.group(1),party_id=chain_impact.group(2),valid_at=q.get("valid_at",[None])[0],known_at=q.get("known_at",[None])[0])
                except ValueError as e: return self.send_json({"error":str(e)},404)
                return self.send_json(impact)
            if path=="/api/chain-tasks":
                cid=q.get("customer_id",[None])[0]
                if not cid:return self.send_json({"error":"customer_id is verplicht"},400)
                return self.send_json(store.chain_tasks(cid,party_id=q.get("party_id",[None])[0]))
            if path=="/api/activities":return self.send_json(store.activities(customer_id=q.get("customer_id",[None])[0]))
            if path=="/api/v1/activities":
                valid_at=q.get("valid_at",[None])[0]; known_at=q.get("known_at",[None])[0]
                if not valid_at or not known_at:return self.send_json({"error":"valid_at en known_at zijn verplicht"},400)
                try: date.fromisoformat(valid_at); store._utc_stamp(known_at)
                except ValueError:return self.send_json({"error":"Ongeldig datum- of tijdformaat"},400)
                return self.send_json(store.activities(customer_id=q.get("customer_id",[None])[0],valid_at=valid_at,known_at=known_at))
            chain_route=re.fullmatch(r"/api/customers/([\w-]+)/activity-chain/([\w-]+)",path)
            if chain_route:
                try: chain=store.activity_chain(customer_id=chain_route.group(1),activity_id=chain_route.group(2),valid_at=q.get("valid_at",[None])[0],known_at=q.get("known_at",[None])[0])
                except ValueError as e: return self.send_json({"error":str(e)},404)
                return self.send_json(chain)
            if path=="/api/v1/dora-assessments":
                valid_at=q.get("valid_at",[None])[0]; known_at=q.get("known_at",[None])[0]
                if not valid_at or not known_at:return self.send_json({"error":"valid_at en known_at zijn verplicht"},400)
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",valid_at):return self.send_json({"error":"valid_at moet ISO-formaat YYYY-MM-DD hebben"},400)
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|\+00:00)?",known_at):return self.send_json({"error":"known_at moet UTC ISO 8601 zijn"},400)
                try: date.fromisoformat(valid_at); store._utc_stamp(known_at)
                except ValueError:return self.send_json({"error":"Ongeldig datum- of tijdformaat"},400)
                return self.send_json(store.dora_assessments(valid_at,known_at,q.get("customer_id",[None])[0]))
            graph_view=re.fullmatch(r"/api/customers/([\w-]+)/graph",path)
            if graph_view:
                graph=store.client_graph(graph_view.group(1),q.get("valid_at",[None])[0],q.get("known_at",[None])[0])
                return self.send_json(graph) if graph else self.send_json({"error":"not_found"},404)
            graph=re.fullmatch(r"/api/customers/([\w-]+)/(entities|relationships)",path)
            if graph:
                if graph.group(2)=="entities":return self.send_json(store.client_entities(graph.group(1),q.get("valid_at",[None])[0],q.get("known_at",[None])[0]))
                return self.send_json(store.client_relationships(graph.group(1),q.get("valid_at",[None])[0],q.get("known_at",[None])[0]))
            graph_history=re.fullmatch(r"/api/customers/([\w-]+)/graph-history",path)
            if graph_history:
                history=store.graph_knowledge_history(graph_history.group(1))
                return self.send_json(history) if history else self.send_json({"error":"not_found"},404)
            policy_reviews=re.fullmatch(r"/api/policies/([\w-]+)/(\d+)/source-reviews",path)
            if policy_reviews:
                rows=store.policy_source_reviews(policy_reviews.group(1).upper(),int(policy_reviews.group(2))); return self.send_json(rows) if rows is not None else self.send_json({"error":"not_found"},404)
            policy_match=re.fullmatch(r"/api/policies/([\w-]+)",path)
            if policy_match:
                rows=store.policies(policy_match.group(1).upper()); return self.send_json(rows) if rows else self.send_json({"error":"not_found"},404)
            m=re.fullmatch(r"/api/customers/([\w-]+)",path)
            if m:
                item=store.customer(m.group(1),q.get("valid_at",[None])[0],q.get("known_at",[None])[0]); return self.send_json(item) if item else self.send_json({"error":"not_found"},404)
            m=re.fullmatch(r"/api/changes/([\w-]+)",path)
            if m:
                item=store.change(m.group(1)); return self.send_json(item) if item else self.send_json({"error":"not_found"},404)
            m=re.fullmatch(r"/api/exports/([\w-]+)",path)
            if m:
                with store.connect() as db: row=db.execute("SELECT * FROM exports WHERE id=?",(m.group(1),)).fetchone()
                if not row:return self.send_json({"error":"not_found"},404)
                row=dict(row); row["payload"]=json.loads(row["payload"]); return self.send_json(row)
            if path=="/":
                raw=(ROOT/"static"/"index.html").read_bytes()
                addon=(ROOT/"static"/"discovery-workbench.js").read_text()
                workflow=(ROOT/"static"/"workflow-pages.js").read_text()
                theme=(ROOT/"static"/"institutional-theme.css").read_text()
                raw=raw.replace(b"</head>", ("<style>"+theme+"</style></head>").encode())
                raw=raw.replace(b"</body>", ("<script>"+addon+"</script><script>"+workflow+"</script></body>").encode())
                self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw); return
            file=ROOT/"static"/("index.html" if path=="/" else path.removeprefix("/"))
            if not file.resolve().is_relative_to((ROOT/"static").resolve()) or not file.is_file():return self.send_json({"error":"not_found"},404)
            raw=file.read_bytes(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8" if file.suffix==".html" else "text/plain; charset=utf-8"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
        except Exception as e:self.send_json({"error":str(e)},500)
    def do_POST(self):
        path=urlparse(self.path).path
        try:
            data=self.body()
            if path=="/api/v1/configurations/validate":
                if data.get("customer_id"):
                    customer=store.customer(data["customer_id"])
                    if not customer:return self.send_json({"error":"not_found"},404)
                    configuration=customer["payload"]
                    version=data.get("schema_version",customer.get("schema_version","1"))
                else:
                    configuration=data.get("configuration")
                    version=data.get("schema_version")
                if not isinstance(configuration,dict):return self.send_json({"error":"configuration moet een JSON-object zijn"},400)
                actor=str(data.get("actor","")).strip(); reason=str(data.get("reason","")).strip()
                if not actor or not reason:return self.send_json({"error":"actor en reden zijn verplicht voor validatie-audit"},400)
                result=store.validate_configuration(configuration,version)
                store.audit_configuration_validation(configuration,result,actor,reason)
                return self.send_json(result)
            if path=="/api/v1/discovery/decisions":
                return self.send_json(store.save_discovery_decision(data),201)
            if path=="/api/client-requirements":return self.send_json(store.save_client_requirement(data),201)
            if path=="/api/dora-assessments":return self.send_json(store.save_dora_assessment(data),201)
            if path=="/api/activities":
                try: return self.send_json(store.save_activity(data),201)
                except ValueError as e: return self.send_json({"error":str(e)},400)
            if path=="/api/chain-parties":
                try: return self.send_json(store.save_chain_party(data),201)
                except ValueError as e: return self.send_json({"error":str(e)},400)
            if path=="/api/chain-tasks":
                try: return self.send_json(store.save_chain_task(data),201)
                except ValueError as e: return self.send_json({"error":str(e)},400)
            chain_complete=re.fullmatch(r"/api/chain-tasks/([\w-]+)/complete",path)
            if chain_complete:
                try: return self.send_json(store.complete_chain_task(task_id=chain_complete.group(1),customer_id=data.get("customer_id"),evidence=data.get("completion_evidence"),actor=data.get("actor")),201)
                except ValueError as e: return self.send_json({"error":str(e)},400)
            if path=="/api/client-entities":return self.send_json(store.save_client_entity(data),201)
            if path=="/api/client-relationships":return self.send_json(store.save_client_relationship(data),201)
            if path=="/api/changes":return self.send_json(store.create_change(data),201)
            if path=="/api/policies":return self.send_json(store.save_policy(data),201)
            policy_source_review=re.fullmatch(r"/api/policies/([\w-]+)/(\d+)/source-reviews",path)
            if policy_source_review:return self.send_json(store.add_policy_source_review(policy_source_review.group(1).upper(),int(policy_source_review.group(2)),data),201)
            policy_decision=re.fullmatch(r"/api/policies/([\w-]+)/(\d+)/decisions",path)
            if policy_decision:return self.send_json(store.decide_policy(policy_decision.group(1).upper(),int(policy_decision.group(2)),data),201)
            policy_revision=re.fullmatch(r"/api/policies/([\w-]+)/revisions",path)
            if policy_revision:return self.send_json(store.save_policy(data,policy_revision.group(1).upper()),201)
            m=re.fullmatch(r"/api/changes/([\w-]+)/simulate",path)
            if m:return self.send_json(store.simulate(m.group(1),data))
            m=re.fullmatch(r"/api/changes/([\w-]+)/approve",path)
            if m:return self.send_json(store.approve(m.group(1),data))
            m=re.fullmatch(r"/api/changes/([\w-]+)/activate",path)
            if m:return self.send_json(store.activate(m.group(1),data))
            m=re.fullmatch(r"/api/customers/([\w-]+)/export",path)
            if m:
                result=store.export_config(m.group(1),data.get("profile_id","generic-asp"),data.get("actor","demo.publisher"),data.get("valid_at"))
                return self.send_json(result,200,{"Content-Disposition":f'attachment; filename="{result["filename"]}"'})
            return self.send_json({"error":"not_found"},404)
        except (ValueError,KeyError,json.JSONDecodeError) as e:return self.send_json({"error":str(e)},400)
        except Exception as e:return self.send_json({"error":str(e)},500)
    def log_message(self,fmt,*args):print("%s - %s"%(self.address_string(),fmt%args),flush=True)
if __name__=="__main__":
    host=os.environ.get("CLIENT_CONFIG_HOST","127.0.0.1"); port=int(os.environ.get("CLIENT_CONFIG_PORT","8080")); server=ThreadingHTTPServer((host,port),Handler); print(f"Client Config MVP listening on http://{host}:{port}")
    try: server.serve_forever()
    except KeyboardInterrupt: print("Client Config MVP stopped")
    finally: server.server_close()
