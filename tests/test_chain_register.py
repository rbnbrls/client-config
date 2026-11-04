import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="cr-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

DIRECT=dict(customer_id="northstar",party_type="direct",name="Synth Beheer BV",
    service="FIDUCIARY",data_flow="mandates-layouts (dagelijks)",
    jurisdiction="NL",legal_entity="Synth Beheer B.V. (KvK 00000000)",
    contract_ref="SYNTHETIC-CONTRACT-001",criticality="hoog",
    subcontract_share=None,source_ref="SYNTHETIC-CONTRACT-001",rationale="directe aanbieder",
    effective_from="2026-01-01",actor="demo.client-service")

def indirect(cid="northstar",name="Sub Data Services",parent="synth-beheer",service="RISK"):
    return dict(customer_id=cid,party_type="indirect",name=name,service=service,
        data_flow="risicosignalen (dagelijks)",jurisdiction="DE",
        legal_entity="Sub Data Services GmbH",contract_ref="SYNTHETIC-SUBCONTRACT-001",
        parent_party_id=parent,criticality="gemiddeld",subcontract_share=0.35,
        source_ref="SYNTHETIC-SUBCONTRACT-001",rationale="onderuitbesteding",
        effective_from="2026-01-01",actor="demo.client-service")

class CR(unittest.TestCase):
    def setUp(self): isolated_db()
    def test_register_party(self):
        p=store.save_chain_party({**DIRECT,"id":"synth-beheer"})
        self.assertEqual(p["party_type"],"direct")
        self.assertEqual(p["version"],1)
    def test_required_fields(self):
        for key in ("name","service","data_flow","jurisdiction","legal_entity","contract_ref","criticality","source_ref"):
            with self.assertRaises(ValueError):
                store.save_chain_party({**DIRECT,"id":"x",key:None})
    def test_party_type_enum(self):
        with self.assertRaises(ValueError):
            store.save_chain_party({**DIRECT,"id":"x","party_type":"onbekend"})
    def test_versioned_no_overwrite(self):
        p=store.save_chain_party({**DIRECT,"id":"synth-beheer"})
        store.save_chain_party({**p,"criticality":"gemiddeld","rationale":"herbeoordeling"})
        with store.connect() as db:
            vers=[r["version"] for r in db.execute("SELECT version FROM chain_parties WHERE id=?",("synth-beheer",)).fetchall()]
        self.assertEqual(sorted(vers),[1,2])
        latest=[r for r in store.chain_parties(customer_id="northstar") if r["id"]=="synth-beheer"][0]
        self.assertEqual(latest["criticality"],"gemiddeld")
    def test_append_only_delete_blocked(self):
        import sqlite3
        p=store.save_chain_party({**DIRECT,"id":"synth-beheer"})
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM chain_parties WHERE id=?",("synth-beheer",))
    def test_unknown_parent_rejected(self):
        with self.assertRaises(ValueError):
            store.save_chain_party({**indirect()})
    def test_parent_cycle_rejected(self):
        store.save_chain_party({**DIRECT,"id":"synth-beheer"})
        store.save_chain_party({**indirect(),"id":"sub-data","parent_party_id":"synth-beheer"})
        # directe aanbieder herpositioneren onder zijn eigen onderaannemer moet geweigerd worden
        with self.assertRaises(ValueError):
            store.save_chain_party({**DIRECT,"id":"synth-beheer","parent_party_id":"sub-data","version":2,"rationale":"cyclus"})
    def test_chain_trace_direct_and_indirect(self):
        store.save_chain_party({**DIRECT,"id":"synth-beheer"})
        store.save_chain_party({**indirect(),"id":"sub-data"})
        store.save_chain_party({**indirect(name="Sub Sub Analytics",parent="sub-data",service="DATA"),"id":"sub-sub"})
        trace=store.chain_trace(customer_id="northstar",party_id="synth-beheer")
        self.assertIn("synth-beheer",[p["id"] for p in trace["upstream"]])
        downstream={p["id"] for p in trace["downstream"]}
        self.assertEqual(downstream,{"sub-data","sub-sub"})
        levels={p["id"]:p["depth"] for p in trace["downstream"]}
        self.assertEqual(levels["sub-data"],1)
        self.assertEqual(levels["sub-sub"],2)
    def test_chain_impact_identifies_mandates(self):
        store.save_activity(dict(customer_id="northstar",activity_code="OUT-002-FID",
            title="Fiduciair beheer",description="d",boundaries="b",
            services=["FIDUCIARY"],fund_mandate_ref="Strategisch mandaat A",
            criticality="hoog",materiality="materieel",owner="demo.client-service",
            contract_start="2026-01-01",source_ref="SYNTHETIC-CONTRACT-001",
            rationale="r",effective_from="2026-01-01"))
        store.save_chain_party({**DIRECT,"id":"synth-beheer"})
        store.save_chain_party({**indirect(),"id":"sub-data"})
        impact=store.chain_impact(customer_id="northstar",party_id="synth-beheer")
        self.assertIn("synth-beheer",[p["id"] for p in impact["changed_party_and_downstream"]])
        self.assertTrue(any(a["fund_mandate_ref"]=="Strategisch mandaat A" for a in impact["affected_mandates"]))
    def test_threshold_is_parameter_with_source(self):
        store.save_chain_party({**DIRECT,"id":"synth-beheer"})
        store.save_chain_party({**indirect(),"id":"sub-data"})  # share 0.35
        impact=store.chain_impact(customer_id="northstar",party_id="synth-beheer",
            thresholds={"subcontract_share_pct":30,"source_ref":"DNB-verwachting 30% onderuitbesteding; klantspecifiek te bevestigen"})
        flagged=[p["id"] for p in impact["threshold_breaches"]]
        self.assertEqual(flagged,["sub-data"])
        self.assertIn("source_ref",impact["threshold_parameters"])
        # strengere klantspecifieke parameter vangt anders
        impact2=store.chain_impact(customer_id="northstar",party_id="synth-beheer",
            thresholds={"subcontract_share_pct":40,"source_ref":"klant-X-norm"})
        self.assertEqual(impact2["threshold_breaches"],[])
        self.assertEqual(impact2["threshold_parameters"]["source_ref"],"klant-X-norm")
    def test_notification_task_requires_owner_and_deadline(self):
        store.save_chain_party({**DIRECT,"id":"synth-beheer"})
        base=dict(customer_id="northstar",party_id="synth-beheer",task_type="melding",
            rationale="wijziging schakel",actor="demo.compliance")
        with self.assertRaises(ValueError): store.save_chain_task({**base,"owner":None,"deadline":"2026-12-01"})
        with self.assertRaises(ValueError): store.save_chain_task({**base,"owner":"demo.compliance","deadline":None})
        t=store.save_chain_task({**base,"owner":"demo.compliance","deadline":"2026-12-01"})
        self.assertEqual(t["status"],"open")
    def test_task_completion_requires_evidence(self):
        store.save_chain_party({**DIRECT,"id":"synth-beheer"})
        t=store.save_chain_task(dict(customer_id="northstar",party_id="synth-beheer",
            task_type="melding",owner="demo.compliance",deadline="2026-12-01",
            rationale="wijziging",actor="demo.compliance"))
        with self.assertRaises(ValueError):
            store.complete_chain_task(task_id=t["id"],customer_id="northstar",evidence=None)
        done=store.complete_chain_task(task_id=t["id"],customer_id="northstar",evidence="SYNTH-EVIDENCE-001")
        self.assertEqual(done["status"],"completed")
        self.assertEqual(done["completion_evidence"],"SYNTH-EVIDENCE-001")
    def test_valid_time_filter(self):
        store.save_chain_party({**DIRECT,"id":"synth-beheer","effective_from":"2026-06-01"})
        rows=store.chain_parties(customer_id="northstar",valid_at="2026-05-01",known_at="2099-01-01T00:00:00Z")
        self.assertFalse(any(r["id"]=="synth-beheer" for r in rows))
        rows=store.chain_parties(customer_id="northstar",valid_at="2026-07-01",known_at="2099-01-01T00:00:00Z")
        self.assertTrue(any(r["id"]=="synth-beheer" for r in rows))
    def test_impact_unknown_party(self):
        with self.assertRaises(ValueError):
            store.chain_impact(customer_id="northstar",party_id="onbekend")

if __name__=="__main__": unittest.main()
