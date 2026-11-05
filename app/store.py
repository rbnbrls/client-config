"""SQLite persistence, temporal reads, workflow, simulation and exports."""
import hashlib, json, os, re, sqlite3, uuid
from datetime import date, datetime, timezone
from pathlib import Path
from .domain import fee_delta
from . import config_schema

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("CLIENT_CONFIG_DB", ROOT / "data" / "client_config.db"))
def now(): return datetime.now(timezone.utc).isoformat(timespec="microseconds")
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db=sqlite3.connect(DB_PATH); db.row_factory=sqlite3.Row; db.execute("PRAGMA foreign_keys=ON"); return db

def seed(db):
    stamp=now()
    customers=[("northstar","Northstar Pensioenfonds (synthetisch)","Pensioenfonds"),("harbor","Harbor Verzekeringen (synthetisch)","Verzekeraar"),("meridian","Meridian Bank (synthetisch)","Bank")]
    for cid,name,kind in customers:
        db.execute("INSERT INTO customers VALUES(?,?,?,?,?,?)",(cid,name,kind,"NL","Professioneel",stamp))
        payload={"legal_entities":[{"name":name,"role":"client"}],"services":[{"code":"FIDUCIARY","name":"Fiduciair management","status":"active"},{"code":"RISK","name":"Risicomanagement","status":"active"}],"mandate":{"name":"Strategisch mandaat","benchmark":"Synthetic Global 60/40","currency":"EUR","delegation":"Advisory"},"fees":{"type":"aum_bps","bps":18 if cid=="northstar" else 16,"minimum_eur":45000,"frequency":"quarterly"},"sla":{"metric":"rapportage_tijdigheid","target_percent":98,"period":"quarterly"},"reporting":{"frequency":"quarterly","deadline_business_days":10,"language":"nl","recipients":["synthetic.contact@example.invalid"]},"governance":{"committee":"Beleggingscommissie","escalation":"Client lead → Risk"},"restrictions":["Synthetisch voorbeeld; geen echte restrictie"],"evidence":[{"type":"contract","reference":"SYNTHETIC-CONTRACT-001","status":"example only"}]}
        schema_version=str(config_schema.latest_schema(datetime.now(timezone.utc).date().isoformat())["x-version"])
        errors=config_schema.validate(payload,config_schema.get_schema(schema_version))
        if errors: raise ValueError(f"Seedconfiguratie voldoet niet aan schema v{schema_version}: {errors}")
        db.execute("INSERT INTO config_versions(id,customer_id,version,valid_from,valid_to,recorded_from,recorded_to,payload,change_id,schema_version) VALUES(?,?,?,?,?,?,?,?,?,?)",(str(uuid.uuid4()),cid,1,"2026-01-01",None,stamp,None,json.dumps(payload),None,schema_version))
    db.execute("INSERT OR IGNORE INTO partner_profiles VALUES(?,?,?,?)",("generic-asp","Generieke Asset Service Provider","1.0",json.dumps({"customer":"customer","services":"service_catalog","mandate":"mandate","fee_terms":"fees","reporting":"reporting","sla":"sla"})))

def init():
    with connect() as db:
        db.executescript('''CREATE TABLE IF NOT EXISTS customers(id TEXT PRIMARY KEY,name TEXT NOT NULL,kind TEXT NOT NULL,jurisdiction TEXT NOT NULL,classification TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS config_versions(id TEXT PRIMARY KEY,customer_id TEXT NOT NULL REFERENCES customers(id),version INTEGER NOT NULL,valid_from TEXT NOT NULL,valid_to TEXT,recorded_from TEXT NOT NULL,recorded_to TEXT,payload TEXT NOT NULL,change_id TEXT,schema_version TEXT NOT NULL DEFAULT '1',UNIQUE(customer_id,version));
        CREATE INDEX IF NOT EXISTS config_asof ON config_versions(customer_id,valid_from,valid_to,recorded_from,recorded_to);
        CREATE TABLE IF NOT EXISTS config_knowledge_snapshots(id TEXT PRIMARY KEY,customer_id TEXT NOT NULL REFERENCES customers(id),revision INTEGER NOT NULL,recorded_at TEXT NOT NULL,actor TEXT NOT NULL,reason TEXT NOT NULL,timeline TEXT NOT NULL,UNIQUE(customer_id,revision));
        CREATE INDEX IF NOT EXISTS config_knowledge_asof ON config_knowledge_snapshots(customer_id,recorded_at,revision);
        CREATE TRIGGER IF NOT EXISTS config_knowledge_no_update BEFORE UPDATE ON config_knowledge_snapshots BEGIN SELECT RAISE(ABORT,'config knowledge snapshots are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS config_knowledge_no_delete BEFORE DELETE ON config_knowledge_snapshots BEGIN SELECT RAISE(ABORT,'config knowledge snapshots are append-only'); END;
        CREATE TABLE IF NOT EXISTS change_sets(id TEXT PRIMARY KEY,title TEXT NOT NULL,customer_id TEXT NOT NULL REFERENCES customers(id),base_version INTEGER NOT NULL,patch TEXT NOT NULL,effective_date TEXT NOT NULL,rationale TEXT NOT NULL,status TEXT NOT NULL,created_by TEXT NOT NULL,created_at TEXT NOT NULL,simulation TEXT,approved_by TEXT,approved_at TEXT,activated_at TEXT,schema_version TEXT NOT NULL DEFAULT '1');
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,entity_type TEXT NOT NULL,entity_id TEXT NOT NULL,action TEXT NOT NULL,actor TEXT NOT NULL,reason TEXT NOT NULL,at TEXT NOT NULL,details TEXT NOT NULL,old_value TEXT,new_value TEXT,evidence TEXT,policy_version TEXT,schema_version TEXT,simulation TEXT,approval TEXT,activation TEXT,publication_status TEXT);
        CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,'audit records are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,'audit records are append-only'); END;
        CREATE TABLE IF NOT EXISTS partner_profiles(id TEXT PRIMARY KEY,name TEXT NOT NULL,schema_version TEXT NOT NULL,mapping TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS exports(id TEXT PRIMARY KEY,customer_id TEXT NOT NULL,config_version INTEGER NOT NULL,profile_id TEXT NOT NULL,schema_version TEXT NOT NULL,checksum TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL,created_by TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS config_schema_versions(version INTEGER PRIMARY KEY,schema_id TEXT NOT NULL,title TEXT NOT NULL,owner TEXT NOT NULL,effective_from TEXT NOT NULL,recorded_at TEXT NOT NULL,schema_json TEXT NOT NULL,created_by TEXT NOT NULL,rationale TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS config_schema_no_update BEFORE UPDATE ON config_schema_versions BEGIN SELECT RAISE(ABORT,'configuration schemas are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS config_schema_no_delete BEFORE DELETE ON config_schema_versions BEGIN SELECT RAISE(ABORT,'configuration schemas are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS policy_controls(
          id TEXT PRIMARY KEY, control_code TEXT NOT NULL, version INTEGER NOT NULL,
          title TEXT NOT NULL, owner TEXT NOT NULL, audience TEXT NOT NULL,
          source_ref TEXT NOT NULL, applicability TEXT NOT NULL, enforcement TEXT NOT NULL,
          effective_date TEXT NOT NULL, review_date TEXT NOT NULL,
          validation_status TEXT NOT NULL, validation_evidence TEXT NOT NULL,
          created_by TEXT NOT NULL, created_at TEXT NOT NULL, change_note TEXT NOT NULL,
          UNIQUE(control_code,version));
          CREATE INDEX IF NOT EXISTS policy_code_version ON policy_controls(control_code,version);
          CREATE TRIGGER IF NOT EXISTS policy_controls_no_update BEFORE UPDATE ON policy_controls BEGIN SELECT RAISE(ABORT,'policy controls are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS policy_controls_no_delete BEFORE DELETE ON policy_controls BEGIN SELECT RAISE(ABORT,'policy controls are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS policy_source_reviews(
          id TEXT PRIMARY KEY, control_code TEXT NOT NULL, policy_version INTEGER NOT NULL,
          source_kind TEXT NOT NULL, source_title TEXT NOT NULL, source_locator TEXT NOT NULL,
          outcome TEXT NOT NULL, reviewer TEXT NOT NULL, reviewer_role TEXT NOT NULL,
          rationale TEXT NOT NULL, checked_at TEXT NOT NULL);
          CREATE INDEX IF NOT EXISTS policy_source_review_version ON policy_source_reviews(control_code,policy_version,checked_at);
          CREATE TABLE IF NOT EXISTS policy_decisions(
          id TEXT PRIMARY KEY, control_code TEXT NOT NULL, policy_version INTEGER NOT NULL,
          source_review_id TEXT, decision TEXT NOT NULL, reviewer TEXT NOT NULL,
          reviewer_role TEXT NOT NULL, rationale TEXT NOT NULL, decided_at TEXT NOT NULL);
          CREATE INDEX IF NOT EXISTS policy_decision_version ON policy_decisions(control_code,policy_version,decided_at);
          CREATE TRIGGER IF NOT EXISTS policy_source_reviews_no_update BEFORE UPDATE ON policy_source_reviews BEGIN SELECT RAISE(ABORT,'policy source reviews are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS policy_source_reviews_no_delete BEFORE DELETE ON policy_source_reviews BEGIN SELECT RAISE(ABORT,'policy source reviews are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS policy_decisions_no_update BEFORE UPDATE ON policy_decisions BEGIN SELECT RAISE(ABORT,'policy decisions are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS policy_decisions_no_delete BEFORE DELETE ON policy_decisions BEGIN SELECT RAISE(ABORT,'policy decisions are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS client_variants(
          id TEXT NOT NULL, version INTEGER NOT NULL, control_code TEXT NOT NULL,
          policy_version INTEGER NOT NULL, client_id TEXT NOT NULL, fund_id TEXT,
          contractual_requirement TEXT NOT NULL, source_ref TEXT NOT NULL,
          reconciliation_status TEXT NOT NULL, effective_date TEXT NOT NULL,
          owner TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          rationale TEXT NOT NULL,
          PRIMARY KEY(id,version),
          FOREIGN KEY(control_code,policy_version) REFERENCES policy_controls(control_code,version));
          CREATE INDEX IF NOT EXISTS client_variant_control ON client_variants(control_code,policy_version);
          CREATE INDEX IF NOT EXISTS client_variant_client ON client_variants(client_id,id,version);
          CREATE TRIGGER IF NOT EXISTS client_variants_no_update BEFORE UPDATE ON client_variants BEGIN SELECT RAISE(ABORT,'client variants are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS client_variants_no_delete BEFORE DELETE ON client_variants BEGIN SELECT RAISE(ABORT,'client variants are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS client_requirements(
          id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
          category TEXT NOT NULL, title TEXT NOT NULL, requirement TEXT NOT NULL,
          source_ref TEXT NOT NULL, config_path TEXT, expected_value TEXT,
          frequency TEXT NOT NULL, effective_date TEXT NOT NULL, review_date TEXT NOT NULL,
          created_by TEXT NOT NULL, created_at TEXT NOT NULL, rationale TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS client_requirement_customer ON client_requirements(customer_id,id,version);''')
        db.executescript('''CREATE TABLE IF NOT EXISTS dora_assessments(
          id TEXT NOT NULL, version INTEGER NOT NULL, assessment_type TEXT NOT NULL,
          customer_id TEXT REFERENCES customers(id), counterparty TEXT NOT NULL,
          service_name TEXT NOT NULL, scope_description TEXT NOT NULL,
          applicability TEXT NOT NULL, criticality TEXT NOT NULL, contract_ref TEXT NOT NULL,
          source_ref TEXT NOT NULL, reviewer TEXT NOT NULL, reviewer_role TEXT NOT NULL,
          rationale TEXT NOT NULL, review_date TEXT NOT NULL, created_at TEXT NOT NULL,
          effective_from TEXT, effective_to TEXT, PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS dora_assessment_latest ON dora_assessments(id,version);
          CREATE TRIGGER IF NOT EXISTS dora_assessment_no_update BEFORE UPDATE ON dora_assessments BEGIN SELECT RAISE(ABORT,'DORA assessments are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS dora_assessment_no_delete BEFORE DELETE ON dora_assessments BEGIN SELECT RAISE(ABORT,'DORA assessments are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS ict_provider_relations(
          id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT REFERENCES customers(id),
          provider TEXT NOT NULL, ict_service TEXT NOT NULL, function_classification TEXT NOT NULL,
          contract_ref TEXT NOT NULL, incident_evidence TEXT NOT NULL, exit_evidence TEXT NOT NULL,
          applicability TEXT NOT NULL, source_ref TEXT NOT NULL, reviewer TEXT NOT NULL,
          reviewer_role TEXT NOT NULL, rationale TEXT NOT NULL, review_date TEXT NOT NULL,
          created_at TEXT NOT NULL, effective_from TEXT, effective_to TEXT,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS ict_provider_relation_latest ON ict_provider_relations(id,version);
          CREATE TRIGGER IF NOT EXISTS ict_provider_relation_no_update BEFORE UPDATE ON ict_provider_relations BEGIN SELECT RAISE(ABORT,'ICT provider relations are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS ict_provider_relation_no_delete BEFORE DELETE ON ict_provider_relations BEGIN SELECT RAISE(ABORT,'ICT provider relations are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS governance_policies(
          id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT REFERENCES customers(id),
          policy TEXT NOT NULL, monitoring_frequency TEXT NOT NULL, reporting TEXT NOT NULL,
          escalation TEXT NOT NULL, independent_evaluation TEXT NOT NULL, capacity TEXT NOT NULL,
          evaluation_date TEXT NOT NULL, applicability TEXT NOT NULL, source_ref TEXT NOT NULL,
          reviewer TEXT NOT NULL, reviewer_role TEXT NOT NULL, rationale TEXT NOT NULL,
          review_date TEXT NOT NULL, created_at TEXT NOT NULL, effective_from TEXT, effective_to TEXT,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS governance_policy_latest ON governance_policies(id,version);
          CREATE TRIGGER IF NOT EXISTS governance_policy_no_update BEFORE UPDATE ON governance_policies BEGIN SELECT RAISE(ABORT,'Governance policies are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS governance_policy_no_delete BEFORE DELETE ON governance_policies BEGIN SELECT RAISE(ABORT,'Governance policies are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS client_entities(
          id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
          entity_type TEXT NOT NULL, name TEXT NOT NULL, legal_identifier TEXT NOT NULL,
          jurisdiction TEXT NOT NULL, classification TEXT NOT NULL, effective_from TEXT NOT NULL,
          effective_to TEXT, source_ref TEXT NOT NULL, rationale TEXT NOT NULL,
          created_by TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS client_entity_latest ON client_entities(customer_id,id,version);
          CREATE TRIGGER IF NOT EXISTS client_entities_no_update BEFORE UPDATE ON client_entities BEGIN SELECT RAISE(ABORT,'client entities are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS client_entities_no_delete BEFORE DELETE ON client_entities BEGIN SELECT RAISE(ABORT,'client entities are append-only'); END;
          CREATE TABLE IF NOT EXISTS client_relationships(
          id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
          from_entity_id TEXT NOT NULL, to_entity_id TEXT NOT NULL, relationship_type TEXT NOT NULL,
          service_scope TEXT NOT NULL, effective_from TEXT NOT NULL, effective_to TEXT,
          source_ref TEXT NOT NULL, rationale TEXT NOT NULL, created_by TEXT NOT NULL,
          created_at TEXT NOT NULL, PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS client_relationship_latest ON client_relationships(customer_id,id,version);
          CREATE TRIGGER IF NOT EXISTS client_relationships_no_update BEFORE UPDATE ON client_relationships BEGIN SELECT RAISE(ABORT,'client relationships are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS client_relationships_no_delete BEFORE DELETE ON client_relationships BEGIN SELECT RAISE(ABORT,'client relationships are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS graph_knowledge_snapshots(
          id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(id), revision INTEGER NOT NULL,
          recorded_at TEXT NOT NULL, actor TEXT NOT NULL, reason TEXT NOT NULL, timeline TEXT NOT NULL,
          UNIQUE(customer_id,revision));
          CREATE INDEX IF NOT EXISTS graph_knowledge_asof ON graph_knowledge_snapshots(customer_id,recorded_at,revision);
          CREATE TRIGGER IF NOT EXISTS graph_knowledge_no_update BEFORE UPDATE ON graph_knowledge_snapshots BEGIN SELECT RAISE(ABORT,'graph knowledge snapshots are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS graph_knowledge_no_delete BEFORE DELETE ON graph_knowledge_snapshots BEGIN SELECT RAISE(ABORT,'graph knowledge snapshots are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS document_references(
          id TEXT NOT NULL, version INTEGER NOT NULL,
          subject_type TEXT NOT NULL, subject_id TEXT NOT NULL, subject_version INTEGER NOT NULL,
          document_type TEXT NOT NULL, document_date TEXT NOT NULL, owner TEXT NOT NULL,
          confidentiality TEXT NOT NULL, retention_class TEXT NOT NULL, storage_ref TEXT NOT NULL,
          rationale TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS document_reference_subject ON document_references(subject_type,subject_id,subject_version);
          CREATE TRIGGER IF NOT EXISTS document_reference_no_update BEFORE UPDATE ON document_references BEGIN SELECT RAISE(ABORT,'document references are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS document_reference_no_delete BEFORE DELETE ON document_references BEGIN SELECT RAISE(ABORT,'document references are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS activity_register(
          id TEXT NOT NULL, version INTEGER NOT NULL,
          customer_id TEXT NOT NULL REFERENCES customers(id),
          activity_code TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL,
          boundaries TEXT NOT NULL, services TEXT NOT NULL, fund_mandate_ref TEXT,
          criticality TEXT NOT NULL, materiality TEXT NOT NULL, owner TEXT NOT NULL,
          contract_start TEXT NOT NULL, contract_end TEXT,
          source_ref TEXT NOT NULL, effective_from TEXT NOT NULL, effective_to TEXT,
          rationale TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS activity_register_customer ON activity_register(customer_id,id,version);
          CREATE TRIGGER IF NOT EXISTS activity_register_no_update BEFORE UPDATE ON activity_register BEGIN SELECT RAISE(ABORT,'activity register entries are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS activity_register_no_delete BEFORE DELETE ON activity_register BEGIN SELECT RAISE(ABORT,'activity register entries are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS chain_parties(
          id TEXT NOT NULL, version INTEGER NOT NULL,
          customer_id TEXT NOT NULL REFERENCES customers(id),
          party_type TEXT NOT NULL, name TEXT NOT NULL, service TEXT NOT NULL,
          data_flow TEXT NOT NULL, jurisdiction TEXT NOT NULL, legal_entity TEXT NOT NULL,
          contract_ref TEXT NOT NULL, parent_party_id TEXT,
          criticality TEXT NOT NULL, subcontract_share REAL,
          source_ref TEXT NOT NULL, effective_from TEXT NOT NULL, effective_to TEXT,
          rationale TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS chain_parties_customer ON chain_parties(customer_id,id,version);
          CREATE TRIGGER IF NOT EXISTS chain_parties_no_update BEFORE UPDATE ON chain_parties BEGIN SELECT RAISE(ABORT,'chain parties are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS chain_parties_no_delete BEFORE DELETE ON chain_parties BEGIN SELECT RAISE(ABORT,'chain parties are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS chain_tasks(
          id TEXT NOT NULL, version INTEGER NOT NULL,
          customer_id TEXT NOT NULL REFERENCES customers(id),
          party_id TEXT NOT NULL, task_type TEXT NOT NULL,
          owner TEXT NOT NULL, deadline TEXT NOT NULL,
          status TEXT NOT NULL, completion_evidence TEXT,
          source_ref TEXT NOT NULL, rationale TEXT NOT NULL,
          created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS chain_tasks_customer ON chain_tasks(customer_id,party_id,version);
          CREATE TRIGGER IF NOT EXISTS chain_tasks_no_update BEFORE UPDATE ON chain_tasks BEGIN SELECT RAISE(ABORT,'chain tasks are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS chain_tasks_no_delete BEFORE DELETE ON chain_tasks BEGIN SELECT RAISE(ABORT,'chain tasks are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS contract_minimums(
          id TEXT NOT NULL, version INTEGER NOT NULL,
          customer_id TEXT NOT NULL REFERENCES customers(id),
          contract_ref TEXT NOT NULL, subject_type TEXT NOT NULL, subject_id TEXT,
          liability TEXT, transfer_of_rights TEXT, subcontracting TEXT,
          info_exchange TEXT, monitoring TEXT, audit_rights TEXT,
          supervisor_access TEXT, evaluation TEXT, term TEXT,
          exit_continuity TEXT, detailed_costs TEXT,
          source_ref TEXT NOT NULL, rationale TEXT NOT NULL,
          created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS contract_minimums_customer ON contract_minimums(customer_id,contract_ref,version);
          CREATE TRIGGER IF NOT EXISTS contract_minimums_no_update BEFORE UPDATE ON contract_minimums BEGIN SELECT RAISE(ABORT,'contract minimums are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS contract_minimums_no_delete BEFORE DELETE ON contract_minimums BEGIN SELECT RAISE(ABORT,'contract minimums are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS selection_assessments(
          id TEXT NOT NULL, version INTEGER NOT NULL,
          customer_id TEXT NOT NULL REFERENCES customers(id),
          fund_ref TEXT NOT NULL, subject_type TEXT NOT NULL, subject_id TEXT,
          license_certification TEXT, financial_solidity TEXT, continuity TEXT,
          risk_management TEXT, integrity TEXT,
          evidence_ref TEXT, review_cycle TEXT, next_review_at TEXT, status TEXT,
          source_ref TEXT NOT NULL, rationale TEXT NOT NULL,
          created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS selection_assessments_customer ON selection_assessments(customer_id,fund_ref,version);
          CREATE TRIGGER IF NOT EXISTS selection_assessments_no_update BEFORE UPDATE ON selection_assessments BEGIN SELECT RAISE(ABORT,'selection assessments are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS selection_assessments_no_delete BEFORE DELETE ON selection_assessments BEGIN SELECT RAISE(ABORT,'selection assessments are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS notification_signals(
          id TEXT NOT NULL, version INTEGER NOT NULL,
          customer_id TEXT NOT NULL REFERENCES customers(id),
          fund_ref TEXT NOT NULL, subject_type TEXT NOT NULL, subject_id TEXT,
          trigger_type TEXT NOT NULL, status TEXT NOT NULL,
          notified_at TEXT, owner TEXT, reference TEXT,
          evidence_ref TEXT, source_ref TEXT NOT NULL, rationale TEXT NOT NULL,
          created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS notification_signals_customer ON notification_signals(customer_id,fund_ref,version);
          CREATE TRIGGER IF NOT EXISTS notification_signals_no_update BEFORE UPDATE ON notification_signals BEGIN SELECT RAISE(ABORT,'notification signals are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS notification_signals_no_delete BEFORE DELETE ON notification_signals BEGIN SELECT RAISE(ABORT,'notification signals are append-only'); END;''')
        # ESG-001 Beleidsprofiel: per klant/fonds en mandaat het geldende MVB/ESG-beleid, doelen,
        # prioriteit (rendement/risico/duurzaamheid), asset-class scope, versie en bronbewijs.
        # De IMVB-invulling leeft hier per klant/fonds; het verlopen IMVB-convenant wordt niet als
        # zelfstandige actuele wettelijke verplichting gemodelleerd (validatienotitie fase P3).
        db.executescript('''CREATE TABLE IF NOT EXISTS esg_policy_profiles(
          id TEXT NOT NULL, version INTEGER NOT NULL,
          customer_id TEXT NOT NULL REFERENCES customers(id),
          fund_ref TEXT NOT NULL, subject_type TEXT NOT NULL, subject_id TEXT,
          policy_framework TEXT NOT NULL, goals TEXT NOT NULL, priority TEXT NOT NULL,
          asset_class_scope TEXT NOT NULL, oeso_ungp_diligence TEXT, imvb_diligence TEXT,
          assessment_methodology TEXT, esg_rating_source TEXT, decision_thresholds TEXT,
          policy_document_version TEXT, evidence_ref TEXT,
          effective_from TEXT NOT NULL, effective_to TEXT, review_cycle TEXT, next_review_at TEXT,
          source_ref TEXT NOT NULL, rationale TEXT NOT NULL,
          created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS esg_policy_profiles_customer ON esg_policy_profiles(customer_id,fund_ref,version);
          CREATE TRIGGER IF NOT EXISTS esg_policy_profiles_no_update BEFORE UPDATE ON esg_policy_profiles BEGIN SELECT RAISE(ABORT,'ESG policy profiles are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS esg_policy_profiles_no_delete BEFORE DELETE ON esg_policy_profiles BEGIN SELECT RAISE(ABORT,'ESG policy profiles are append-only'); END;
          CREATE TABLE IF NOT EXISTS esg_policy_exceptions(
          id TEXT NOT NULL, version INTEGER NOT NULL,
          customer_id TEXT NOT NULL REFERENCES customers(id),
          profile_id TEXT NOT NULL,
          fund_ref TEXT, subject_type TEXT, subject_id TEXT,
          description TEXT NOT NULL, rationale TEXT NOT NULL, approver TEXT NOT NULL,
          scope_description TEXT, effective_from TEXT, end_date TEXT NOT NULL,
          evidence_ref TEXT, source_ref TEXT,
          created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS esg_policy_exceptions_customer ON esg_policy_exceptions(customer_id,profile_id,version);
          CREATE TRIGGER IF NOT EXISTS esg_policy_exceptions_no_update BEFORE UPDATE ON esg_policy_exceptions BEGIN SELECT RAISE(ABORT,'ESG policy exceptions are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS esg_policy_exceptions_no_delete BEFORE DELETE ON esg_policy_exceptions BEGIN SELECT RAISE(ABORT,'ESG policy exceptions are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS esg_manager_selections(
          id TEXT NOT NULL, version INTEGER NOT NULL,
          customer_id TEXT NOT NULL REFERENCES customers(id),
          fund_ref TEXT NOT NULL, manager_ref TEXT NOT NULL, mandate_ref TEXT,
          selection_stage TEXT NOT NULL DEFAULT 'onboarding',
          min_esg_rating TEXT, exclusion_policy TEXT, inclusion_policy TEXT,
          esg_integration TEXT, climate_nature_human_rights TEXT,
          impact_targets_3d TEXT, thresholds TEXT,
          review_moment TEXT, next_review_at TEXT,
          exception_rationale TEXT, exception_approver TEXT, exception_end_date TEXT,
          source_ref TEXT NOT NULL, rationale TEXT NOT NULL,
          created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS esg_manager_selections_customer ON esg_manager_selections(customer_id,fund_ref,version);
          CREATE TRIGGER IF NOT EXISTS esg_manager_selections_no_update BEFORE UPDATE ON esg_manager_selections BEGIN SELECT RAISE(ABORT,'ESG manager selections are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS esg_manager_selections_no_delete BEFORE DELETE ON esg_manager_selections BEGIN SELECT RAISE(ABORT,'ESG manager selections are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS esg_contractual_flowdowns(
          id TEXT NOT NULL, version INTEGER NOT NULL,
          customer_id TEXT NOT NULL REFERENCES customers(id),
          fund_ref TEXT NOT NULL, manager_ref TEXT NOT NULL, sub_manager_ref TEXT,
          target TEXT NOT NULL DEFAULT 'direct_manager',
          clause TEXT NOT NULL,
          obligation_text TEXT,
          review_moment TEXT, next_review_at TEXT,
          exception_rationale TEXT, exception_approver TEXT, exception_end_date TEXT,
          source_ref TEXT NOT NULL, rationale TEXT NOT NULL,
          created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS esg_contractual_flowdowns_customer ON esg_contractual_flowdowns(customer_id,fund_ref,version);
          CREATE TRIGGER IF NOT EXISTS esg_contractual_flowdowns_no_update BEFORE UPDATE ON esg_contractual_flowdowns BEGIN SELECT RAISE(ABORT,'ESG contractual flowdowns are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS esg_contractual_flowdowns_no_delete BEFORE DELETE ON esg_contractual_flowdowns BEGIN SELECT RAISE(ABORT,'ESG contractual flowdowns are append-only'); END;''')
        db.executescript("CREATE TABLE IF NOT EXISTS esg_due_diligence_dossiers(id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id), fund_ref TEXT NOT NULL, manager_ref TEXT NOT NULL, workflow_step TEXT NOT NULL, impact_priority TEXT NOT NULL DEFAULT 'medium', finding TEXT NOT NULL, human_judgement TEXT NOT NULL, action_owner TEXT NOT NULL, deadline TEXT NOT NULL, source_ref TEXT NOT NULL, rationale TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(id,version)); CREATE INDEX IF NOT EXISTS esg_due_diligence_dossiers_customer ON esg_due_diligence_dossiers(customer_id,fund_ref,version); CREATE TRIGGER IF NOT EXISTS esg_due_diligence_dossiers_no_update BEFORE UPDATE ON esg_due_diligence_dossiers BEGIN SELECT RAISE(ABORT,'ESG due diligence dossiers are append-only'); END; CREATE TRIGGER IF NOT EXISTS esg_due_diligence_dossiers_no_delete BEFORE DELETE ON esg_due_diligence_dossiers BEGIN SELECT RAISE(ABORT,'ESG due diligence dossiers are append-only'); END;")
        db.executescript("CREATE TABLE IF NOT EXISTS esg_engagement_incidents(id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id), fund_ref TEXT NOT NULL, manager_ref TEXT NOT NULL, incident TEXT NOT NULL, source_ref TEXT NOT NULL, severity TEXT NOT NULL, engagement_relation TEXT NOT NULL, engagement_goal TEXT NOT NULL, progress TEXT NOT NULL DEFAULT 'open', actions TEXT, remediation TEXT, closure TEXT, retention_decision TEXT NOT NULL DEFAULT 'pending', rationale TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(id,version)); CREATE INDEX IF NOT EXISTS esg_engagement_incidents_customer ON esg_engagement_incidents(customer_id,fund_ref,version); CREATE TRIGGER IF NOT EXISTS esg_engagement_incidents_no_update BEFORE UPDATE ON esg_engagement_incidents BEGIN SELECT RAISE(ABORT,'ESG engagement incidents are append-only'); END; CREATE TRIGGER IF NOT EXISTS esg_engagement_incidents_no_delete BEFORE DELETE ON esg_engagement_incidents BEGIN SELECT RAISE(ABORT,'ESG engagement incidents are append-only'); END;")
        db.executescript("CREATE TABLE IF NOT EXISTS esg_periodic_reviews(id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id), fund_ref TEXT NOT NULL, manager_ref TEXT NOT NULL, review_period TEXT NOT NULL DEFAULT 'annual', esg_risks TEXT NOT NULL, results TEXT NOT NULL, improvement_actions TEXT, deviation TEXT NOT NULL DEFAULT 'none', deviation_rationale TEXT, approver TEXT, end_date TEXT, escalation TEXT NOT NULL DEFAULT 'none', source_ref TEXT NOT NULL, rationale TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(id,version)); CREATE INDEX IF NOT EXISTS esg_periodic_reviews_customer ON esg_periodic_reviews(customer_id,fund_ref,version); CREATE TRIGGER IF NOT EXISTS esg_periodic_reviews_no_update BEFORE UPDATE ON esg_periodic_reviews BEGIN SELECT RAISE(ABORT,'ESG periodic reviews are append-only'); END; CREATE TRIGGER IF NOT EXISTS esg_periodic_reviews_no_delete BEFORE DELETE ON esg_periodic_reviews BEGIN SELECT RAISE(ABORT,'ESG periodic reviews are append-only'); END;")
        db.executescript('''CREATE TABLE IF NOT EXISTS reporting_catalog(
          id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
          report_type TEXT NOT NULL, data_item TEXT NOT NULL, definition TEXT NOT NULL, unit TEXT NOT NULL,
          perimeter TEXT NOT NULL, scope TEXT, calculation_source TEXT NOT NULL,
          frequency TEXT NOT NULL, deadline TEXT, language TEXT NOT NULL DEFAULT 'nl',
          template_ref TEXT, recipients TEXT NOT NULL, schema_version TEXT, methodology_version TEXT,
          source_ref TEXT NOT NULL, rationale TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS reporting_catalog_customer ON reporting_catalog(customer_id,report_type,version);
          CREATE TRIGGER IF NOT EXISTS reporting_catalog_no_update BEFORE UPDATE ON reporting_catalog BEGIN SELECT RAISE(ABORT,'reporting catalog is append-only'); END;
          CREATE TRIGGER IF NOT EXISTS reporting_catalog_no_delete BEFORE DELETE ON reporting_catalog BEGIN SELECT RAISE(ABORT,'reporting catalog is append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS data_delivery_agreements(
          id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
          supplier_ref TEXT NOT NULL, supplier_role TEXT NOT NULL, field TEXT NOT NULL, period TEXT NOT NULL,
          channel TEXT NOT NULL, validation TEXT NOT NULL, proof TEXT NOT NULL,
          source_ref TEXT NOT NULL, rationale TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS data_delivery_agreements_customer ON data_delivery_agreements(customer_id,supplier_role,version);
          CREATE TRIGGER IF NOT EXISTS data_delivery_agreements_no_update BEFORE UPDATE ON data_delivery_agreements BEGIN SELECT RAISE(ABORT,'data delivery agreements are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS data_delivery_agreements_no_delete BEFORE DELETE ON data_delivery_agreements BEGIN SELECT RAISE(ABORT,'data delivery agreements are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS sfdr_pai_profiles(
          id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
          profile_name TEXT NOT NULL, pai_indicators TEXT NOT NULL, reference_period TEXT NOT NULL,
          reporting_frequency TEXT NOT NULL, methodology TEXT NOT NULL, data_coverage TEXT NOT NULL,
          missing_data_reason TEXT NOT NULL, assurance TEXT NOT NULL, responsibility TEXT NOT NULL,
          applicability_decision_ref TEXT NOT NULL, schema_version TEXT, methodology_version TEXT,
          source_ref TEXT NOT NULL, rationale TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS sfdr_pai_profiles_customer ON sfdr_pai_profiles(customer_id,profile_name,version);
          CREATE TRIGGER IF NOT EXISTS sfdr_pai_profiles_no_update BEFORE UPDATE ON sfdr_pai_profiles BEGIN SELECT RAISE(ABORT,'sfdr pai profiles are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS sfdr_pai_profiles_no_delete BEFORE DELETE ON sfdr_pai_profiles BEGIN SELECT RAISE(ABORT,'sfdr pai profiles are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS comply_or_explain(
          id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
          code_ref TEXT NOT NULL, compliance_status TEXT NOT NULL, deviation_explanation TEXT NOT NULL,
          validity_from TEXT NOT NULL, validity_to TEXT NOT NULL, impact TEXT NOT NULL,
          approver TEXT NOT NULL, follow_up_action TEXT NOT NULL,
          source_ref TEXT NOT NULL, rationale TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS comply_or_explain_customer ON comply_or_explain(customer_id,code_ref,version);
          CREATE TRIGGER IF NOT EXISTS comply_or_explain_no_update BEFORE UPDATE ON comply_or_explain BEGIN SELECT RAISE(ABORT,'comply or explain records are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS comply_or_explain_no_delete BEFORE DELETE ON comply_or_explain BEGIN SELECT RAISE(ABORT,'comply or explain records are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS reporting_executions(
          id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
          report_ref TEXT NOT NULL, calendar_period TEXT NOT NULL, deadline TEXT NOT NULL,
          delivery_status TEXT NOT NULL, completeness TEXT NOT NULL, data_quality_errors TEXT,
          delay_days INTEGER NOT NULL DEFAULT 0, incident_ref TEXT, recovery_action TEXT,
          escalation TEXT NOT NULL DEFAULT 'none', approved_report_ref TEXT, schema_version TEXT,
          methodology_version TEXT, source_ref TEXT NOT NULL, rationale TEXT NOT NULL,
          created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS reporting_executions_customer ON reporting_executions(customer_id,report_ref,version);
          CREATE TRIGGER IF NOT EXISTS reporting_executions_no_update BEFORE UPDATE ON reporting_executions BEGIN SELECT RAISE(ABORT,'reporting executions are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS reporting_executions_no_delete BEFORE DELETE ON reporting_executions BEGIN SELECT RAISE(ABORT,'reporting executions are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS transparency_outputs(
          id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
          disclosure_ref TEXT NOT NULL, manager_ref TEXT, data_coverage TEXT,
          confidentiality_flag TEXT NOT NULL DEFAULT 'confidential', publication_consent TEXT NOT NULL DEFAULT 'pending',
          publication_scope TEXT, schema_version TEXT, methodology_version TEXT,
          source_ref TEXT NOT NULL, rationale TEXT NOT NULL,
          created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS transparency_outputs_customer ON transparency_outputs(customer_id,disclosure_ref,version);
          CREATE TRIGGER IF NOT EXISTS transparency_outputs_no_update BEFORE UPDATE ON transparency_outputs BEGIN SELECT RAISE(ABORT,'transparency outputs are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS transparency_outputs_no_delete BEFORE DELETE ON transparency_outputs BEGIN SELECT RAISE(ABORT,'transparency outputs are append-only'); END;''')
        # WTP-001 Transitieprofiel: fondsregeling/transitiefase, planning, scope, relevante
        # besluit-/go-live-/invaardata en eigenaar. Append-only versieer per fonds.
        db.executescript('''CREATE TABLE IF NOT EXISTS wtp_transition_profiles(
          id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
          fund_ref TEXT NOT NULL, fund_regulation TEXT NOT NULL, transition_phase TEXT NOT NULL,
          planning TEXT NOT NULL, scope TEXT NOT NULL, decision_date TEXT, golive_date TEXT, migration_date TEXT,
          owner TEXT NOT NULL, source_ref TEXT NOT NULL, rationale TEXT NOT NULL,
          created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS wtp_transition_profiles_customer ON wtp_transition_profiles(customer_id,fund_ref,version);
          CREATE TRIGGER IF NOT EXISTS wtp_transition_profiles_no_update BEFORE UPDATE ON wtp_transition_profiles BEGIN SELECT RAISE(ABORT,'wtp transition profiles are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS wtp_transition_profiles_no_delete BEFORE DELETE ON wtp_transition_profiles BEGIN SELECT RAISE(ABORT,'wtp transition profiles are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS partner_profiles_versions(
          id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
          partner_id TEXT NOT NULL, partner_name TEXT NOT NULL, format TEXT NOT NULL,
          mapping TEXT NOT NULL, validation TEXT NOT NULL, classification TEXT NOT NULL,
          privacy_filter TEXT NOT NULL, schema_version TEXT NOT NULL, contract_test TEXT NOT NULL,
          source_ref TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS partner_profiles_versions_customer ON partner_profiles_versions(customer_id,partner_id,version);
          CREATE TRIGGER IF NOT EXISTS partner_profiles_versions_no_update BEFORE UPDATE ON partner_profiles_versions BEGIN SELECT RAISE(ABORT,'partner profiles are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS partner_profiles_versions_no_delete BEFORE DELETE ON partner_profiles_versions BEGIN SELECT RAISE(ABORT,'partner profiles are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS publication_status_versions(
          id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
          export_id TEXT NOT NULL, checksum TEXT NOT NULL, snapshot_version TEXT NOT NULL,
          schema_version TEXT NOT NULL, mapping_version TEXT NOT NULL, actor TEXT NOT NULL,
          published_at TEXT NOT NULL, target TEXT NOT NULL, receipt_status TEXT NOT NULL,
          processing_status TEXT NOT NULL, source_ref TEXT NOT NULL,
          created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS publication_status_versions_customer ON publication_status_versions(customer_id,export_id,version);
          CREATE TRIGGER IF NOT EXISTS publication_status_versions_no_update BEFORE UPDATE ON publication_status_versions BEGIN SELECT RAISE(ABORT,'publication status is append-only'); END;
          CREATE TRIGGER IF NOT EXISTS publication_status_versions_no_delete BEFORE DELETE ON publication_status_versions BEGIN SELECT RAISE(ABORT,'publication status is append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS integration_versions(
          id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
          source TEXT NOT NULL, direction TEXT NOT NULL, frequency TEXT NOT NULL,
          data_owner TEXT NOT NULL, contract TEXT NOT NULL, privacy_classification TEXT NOT NULL,
          reconciliation TEXT NOT NULL, endpoint TEXT, actor TEXT NOT NULL,
          source_ref TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS integration_versions_customer ON integration_versions(customer_id,source,version);
          CREATE TRIGGER IF NOT EXISTS integration_versions_no_update BEFORE UPDATE ON integration_versions BEGIN SELECT RAISE(ABORT,'integrations are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS integration_versions_no_delete BEFORE DELETE ON integration_versions BEGIN SELECT RAISE(ABORT,'integrations are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS integration_deliveries(
          id INTEGER PRIMARY KEY AUTOINCREMENT, integration_id TEXT NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
          payload_checksum TEXT NOT NULL, delivery_status TEXT NOT NULL, actor TEXT NOT NULL,
          source_ref TEXT NOT NULL, created_at TEXT NOT NULL);
          CREATE TRIGGER IF NOT EXISTS integration_deliveries_no_update BEFORE UPDATE ON integration_deliveries BEGIN SELECT RAISE(ABORT,'integration deliveries are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS integration_deliveries_no_delete BEFORE DELETE ON integration_deliveries BEGIN SELECT RAISE(ABORT,'integration deliveries are append-only'); END;''')
        # PERF-001 Rendementsmethodiek per mandaat: versioned, append-only method profile.
        db.executescript('''CREATE TABLE IF NOT EXISTS method_profile_versions(
          id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
          mandate TEXT NOT NULL, method TEXT NOT NULL, cashflow_timing TEXT NOT NULL,
          geometric_linking INTEGER NOT NULL DEFAULT 1, gross_net_definition TEXT, fee_accrual TEXT,
          valuation_basis TEXT, price_source_timing TEXT, base_currency TEXT, reporting_currency TEXT,
          fx_source TEXT, fx_fixing TEXT, return_scope TEXT, derivatives_overlay_convention TEXT,
          reporting_periods TEXT, annualisation TEXT, inception_date TEXT,
          actor TEXT NOT NULL, source_ref TEXT NOT NULL, created_by TEXT, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS method_profile_versions_customer ON method_profile_versions(customer_id,mandate,version);
          CREATE TRIGGER IF NOT EXISTS method_profile_versions_no_update BEFORE UPDATE ON method_profile_versions BEGIN SELECT RAISE(ABORT,'method profiles are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS method_profile_versions_no_delete BEFORE DELETE ON method_profile_versions BEGIN SELECT RAISE(ABORT,'method profiles are append-only'); END;''')
        # PERF-002 Pensioenspecifieke portefeuille-indeling: return vs matching/LDI, append-only.
        db.executescript('''CREATE TABLE IF NOT EXISTS pension_portfolio_versions(
          id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
          mandate TEXT NOT NULL, portfolio_type TEXT NOT NULL, swaps_overlay TEXT, hedge_return_vs_underlying TEXT,
          liabilities_benchmark TEXT, term_structure TEXT, coverage_ratio_indicator TEXT, hedge_ratio_indicator TEXT,
          actor TEXT NOT NULL, source_ref TEXT NOT NULL, created_by TEXT, created_at TEXT NOT NULL,
          PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS pension_portfolio_versions_customer ON pension_portfolio_versions(customer_id,mandate,version);
          CREATE TRIGGER IF NOT EXISTS pension_portfolio_versions_no_update BEFORE UPDATE ON pension_portfolio_versions BEGIN SELECT RAISE(ABORT,'pension portfolios are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS pension_portfolio_versions_no_delete BEFORE DELETE ON pension_portfolio_versions BEGIN SELECT RAISE(ABORT,'pension portfolios are append-only'); END;''')
        # BENCH-001 Benchmarkdefinitie: index-ID, aanbieder, return-type, valuta, hedge-status,
        # samengestelde benchmarks met componenten/gewichten/rebalancefrequentie/geldigheidsdata. Append-only.
        db.executescript('''CREATE TABLE IF NOT EXISTS benchmark_versions(
          id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
          name TEXT, benchmark_type TEXT, index_id TEXT, provider TEXT, return_type TEXT NOT NULL,
          currency TEXT, hedge_status TEXT, components TEXT, weights TEXT, rebalance_frequency TEXT,
          valid_from TEXT, valid_to TEXT, effective_date TEXT, history_policy TEXT,
          known_at TEXT, actor TEXT NOT NULL, source_ref TEXT NOT NULL,
          created_by TEXT, created_at TEXT NOT NULL, PRIMARY KEY(id,version));
          CREATE INDEX IF NOT EXISTS benchmark_versions_customer ON benchmark_versions(customer_id,version);
          CREATE TRIGGER IF NOT EXISTS benchmark_versions_no_update BEFORE UPDATE ON benchmark_versions BEGIN SELECT RAISE(ABORT,'benchmarks are append-only'); END;
          CREATE TRIGGER IF NOT EXISTS benchmark_versions_no_delete BEFORE DELETE ON benchmark_versions BEGIN SELECT RAISE(ABORT,'benchmarks are append-only'); END;''')
        # WTP-002 RACI en afhankelijkheden: partijen, taken, input/output, handoff,"
        # WTP-002 RACI en afhankelijkheden: partijen, taken, input/output, handoff,
          # afhankelijkheid en escalatie per fonds. Append-only versieer per id.
        db.executescript('''CREATE TABLE IF NOT EXISTS wtp_raci_dependencies(
            id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
            fund_ref TEXT NOT NULL, party_role TEXT NOT NULL, party_name TEXT NOT NULL,
            task TEXT NOT NULL, input TEXT, output TEXT, handoff TEXT, dependency TEXT,
            escalation TEXT, critical_milestone TEXT, evidence_status TEXT,
            source_ref TEXT NOT NULL, rationale TEXT NOT NULL,
            created_by TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(id,version));
            CREATE INDEX IF NOT EXISTS wtp_raci_dependencies_customer ON wtp_raci_dependencies(customer_id,fund_ref,party_role,version);
            CREATE TRIGGER IF NOT EXISTS wtp_raci_dependencies_no_update BEFORE UPDATE ON wtp_raci_dependencies BEGIN SELECT RAISE(ABORT,'wtp raci dependencies are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS wtp_raci_dependencies_no_delete BEFORE DELETE ON wtp_raci_dependencies BEGIN SELECT RAISE(ABORT,'wtp raci dependencies are append-only'); END;''')
        # WTP-003 Transitiegegevens
        db.executescript('''CREATE TABLE IF NOT EXISTS wtp_transition_data(
            id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
            fund_ref TEXT NOT NULL, data_item TEXT NOT NULL, data_phase TEXT NOT NULL,
            owner TEXT NOT NULL, source TEXT NOT NULL, frequency TEXT NOT NULL,
            validation_rule TEXT NOT NULL, reconciliation TEXT, data_quality_norm TEXT,
            evidence TEXT, continuity_agreement TEXT,
            source_ref TEXT NOT NULL, rationale TEXT NOT NULL,
            created_by TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(id,version));
            CREATE INDEX IF NOT EXISTS wtp_transition_data_customer ON wtp_transition_data(customer_id,fund_ref,data_phase,version);
            CREATE TRIGGER IF NOT EXISTS wtp_transition_data_no_update BEFORE UPDATE ON wtp_transition_data BEGIN SELECT RAISE(ABORT,'wtp transition data are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS wtp_transition_data_no_delete BEFORE DELETE ON wtp_transition_data BEGIN SELECT RAISE(ABORT,'wtp transition data are append-only'); END;''')
        # WTP-004 Mijlpalen en gereedheidscriteria
        db.executescript('''CREATE TABLE IF NOT EXISTS wtp_milestones(
            id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
            fund_ref TEXT NOT NULL, deliverable TEXT NOT NULL, planning TEXT,
            validation_criteria TEXT NOT NULL, progress_report TEXT, risk_impact TEXT,
            recovery_plan TEXT, go_no_go_evidence TEXT, evidence_status TEXT,
            source_ref TEXT NOT NULL, rationale TEXT NOT NULL,
            created_by TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(id,version));
            CREATE INDEX IF NOT EXISTS wtp_milestones_customer ON wtp_milestones(customer_id,fund_ref,deliverable,version);
            CREATE TRIGGER IF NOT EXISTS wtp_milestones_no_update BEFORE UPDATE ON wtp_milestones BEGIN SELECT RAISE(ABORT,'wtp milestones are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS wtp_milestones_no_delete BEFORE DELETE ON wtp_milestones BEGIN SELECT RAISE(ABORT,'wtp milestones are append-only'); END;''')
        # WTP-005 Risico's en wijzigingsbeheer
        db.executescript('''CREATE TABLE IF NOT EXISTS wtp_risks(
            id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
            fund_ref TEXT NOT NULL, risk_category TEXT NOT NULL, risk_description TEXT NOT NULL,
            mitigation TEXT NOT NULL, change_impact TEXT NOT NULL, affected_roles TEXT,
            required_data TEXT, missing_interfaces TEXT, critical_milestone TEXT,
            evidence_status TEXT, source_ref TEXT NOT NULL, rationale TEXT NOT NULL,
            created_by TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(id,version));
            CREATE INDEX IF NOT EXISTS wtp_risks_customer ON wtp_risks(customer_id,fund_ref,risk_category,version);
            CREATE TRIGGER IF NOT EXISTS wtp_risks_no_update BEFORE UPDATE ON wtp_risks BEGIN SELECT RAISE(ABORT,'wtp risks are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS wtp_risks_no_delete BEFORE DELETE ON wtp_risks BEGIN SELECT RAISE(ABORT,'wtp risks are append-only'); END;''')
        # FEE-001 Fee-componenten
        db.executescript('''CREATE TABLE IF NOT EXISTS fee_components(
            id TEXT NOT NULL, version INTEGER NOT NULL, customer_id TEXT NOT NULL REFERENCES customers(id),
            fund_ref TEXT NOT NULL, fee_type TEXT NOT NULL, fee_name TEXT NOT NULL,
            rate_bps REAL, tier_from REAL, tier_to REAL, minimum_amount REAL, minimum_currency TEXT,
            fixed_amount REAL, fixed_currency TEXT, fixed_frequency TEXT,
            performance_fee_pct REAL, hurdle_rate_pct REAL, high_water_mark INTEGER,
            discount_pct REAL, side_letter_ref TEXT, currency TEXT NOT NULL,
            accrual_frequency TEXT NOT NULL, invoice_frequency TEXT NOT NULL,
            indexation_basis TEXT, indexation_frequency TEXT,
            effective_from TEXT, effective_to TEXT,
            source_ref TEXT NOT NULL, rationale TEXT NOT NULL,
            created_by TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(id,version));
            CREATE INDEX IF NOT EXISTS fee_components_customer ON fee_components(customer_id,fund_ref,fee_type,version);
            CREATE TRIGGER IF NOT EXISTS fee_components_no_update BEFORE UPDATE ON fee_components BEGIN SELECT RAISE(ABORT,'fee components are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS fee_components_no_delete BEFORE DELETE ON fee_components BEGIN SELECT RAISE(ABORT,'fee components are append-only'); END;''')
        db.executescript('''CREATE TABLE IF NOT EXISTS fee_calculation_rules(
            id TEXT NOT NULL, version INTEGER NOT NULL,
            customer_id TEXT NOT NULL, fund_ref TEXT NOT NULL, rule_name TEXT NOT NULL,
            base TEXT NOT NULL, measurement_period TEXT NOT NULL, valuation_input TEXT NOT NULL,
            fx_basis TEXT, rounding_mode TEXT NOT NULL, cap_amount REAL, floor_amount REAL,
            edge_case TEXT, effective_from TEXT, effective_to TEXT,
            source_ref TEXT NOT NULL, rationale TEXT NOT NULL, created_by TEXT NOT NULL,
            created_at TEXT NOT NULL, PRIMARY KEY(id,version));''')
        db.executescript('''CREATE INDEX IF NOT EXISTS fee_calc_rules_customer ON fee_calculation_rules(customer_id,fund_ref,rule_name,version);
            CREATE TRIGGER IF NOT EXISTS fee_calc_rules_no_update BEFORE UPDATE ON fee_calculation_rules BEGIN SELECT RAISE(ABORT,'fee calculation rules are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS fee_calc_rules_no_delete BEFORE DELETE ON fee_calculation_rules BEGIN SELECT RAISE(ABORT,'fee calculation rules are append-only'); END;''')
        # FEE-004 Externe managerlijst/look-through
        db.executescript('''CREATE TABLE IF NOT EXISTS manager_look_through(
            id TEXT NOT NULL, version INTEGER NOT NULL,
            customer_id TEXT NOT NULL REFERENCES customers(id),
            manager_ref TEXT NOT NULL, fund_ref TEXT NOT NULL, vehicle_ref TEXT,
            mandate_ref TEXT, asset_class TEXT NOT NULL, aum REAL,
            coverage_date TEXT NOT NULL, disclosure_permission TEXT NOT NULL,
            data_coverage TEXT, source_ref TEXT NOT NULL, rationale TEXT NOT NULL,
            created_by TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(id,version));''')
        db.executescript('''CREATE INDEX IF NOT EXISTS manager_look_through_customer ON manager_look_through(customer_id,manager_ref,fund_ref,version);
            CREATE TRIGGER IF NOT EXISTS manager_look_through_no_update BEFORE UPDATE ON manager_look_through BEGIN SELECT RAISE(ABORT,'manager look-through is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS manager_look_through_no_delete BEFORE DELETE ON manager_look_through BEGIN SELECT RAISE(ABORT,'manager look-through is append-only'); END;''')
        # FEE-005 Simulatie
        db.executescript('''CREATE TABLE IF NOT EXISTS fee_simulation(
            id TEXT NOT NULL, version INTEGER NOT NULL,
            customer_id TEXT NOT NULL REFERENCES customers(id),
            fund_ref TEXT NOT NULL, manager_ref TEXT, product_ref TEXT,
            scenario_name TEXT NOT NULL, level TEXT NOT NULL,
            baseline_amount REAL, scenario_amount REAL, delta_amount REAL,
            missing_inputs TEXT, uncertainty TEXT, source_ref TEXT NOT NULL,
            rationale TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(id,version));''')
        db.executescript('''CREATE INDEX IF NOT EXISTS fee_simulation_customer ON fee_simulation(customer_id,fund_ref,level,version);
            CREATE TRIGGER IF NOT EXISTS fee_simulation_no_update BEFORE UPDATE ON fee_simulation BEGIN SELECT RAISE(ABORT,'fee simulation is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS fee_simulation_no_delete BEFORE DELETE ON fee_simulation BEGIN SELECT RAISE(ABORT,'fee simulation is append-only'); END;''')
        # TWIN-002 Isolatie en reproduceerbaarheid: scenario snapshots (append-only)
        db.executescript('''CREATE TABLE IF NOT EXISTS scenario_snapshots(
            id TEXT NOT NULL, version INTEGER NOT NULL,
            customer_id TEXT NOT NULL REFERENCES customers(id),
            scenario_name TEXT NOT NULL,
            snapshot TEXT NOT NULL, inputs TEXT NOT NULL,
            calc_logic_version TEXT NOT NULL, policy_version TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            outcome TEXT, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(id,version));''')
        db.executescript('''CREATE INDEX IF NOT EXISTS scenario_snapshots_customer ON scenario_snapshots(customer_id,scenario_name,version);
            CREATE TRIGGER IF NOT EXISTS scenario_snapshots_no_update BEFORE UPDATE ON scenario_snapshots BEGIN SELECT RAISE(ABORT,'scenario snapshots are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS scenario_snapshots_no_delete BEFORE DELETE ON scenario_snapshots BEGIN SELECT RAISE(ABORT,'scenario snapshots are append-only'); END;''')
        # FEE-003 Kostenoverzicht
        db.executescript('''CREATE TABLE IF NOT EXISTS cost_overview(
            id TEXT NOT NULL, version INTEGER NOT NULL,
            customer_id TEXT NOT NULL REFERENCES customers(id),
            fund_ref TEXT NOT NULL, mandate_ref TEXT, product_ref TEXT,
            cost_type TEXT NOT NULL, source_ref TEXT NOT NULL, recipient TEXT NOT NULL,
            period_start TEXT NOT NULL, period_end TEXT NOT NULL, perimeter TEXT NOT NULL,
            amount REAL NOT NULL, currency TEXT NOT NULL, allocation_basis TEXT,
            coverage_pct REAL, effective_from TEXT, effective_to TEXT,
            rationale TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(id,version));''')
        db.executescript('''CREATE INDEX IF NOT EXISTS cost_overview_customer ON cost_overview(customer_id,fund_ref,cost_type,version);
            CREATE TRIGGER IF NOT EXISTS cost_overview_no_update BEFORE UPDATE ON cost_overview BEGIN SELECT RAISE(ABORT,'cost overview is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS cost_overview_no_delete BEFORE DELETE ON cost_overview BEGIN SELECT RAISE(ABORT,'cost overview is append-only'); END;''')
        # TWIN-001 Change-as-code
        db.executescript('''CREATE TABLE IF NOT EXISTS change_as_code(
            id TEXT NOT NULL, version INTEGER NOT NULL,
            customer_id TEXT NOT NULL REFERENCES customers(id),
            entity_type TEXT NOT NULL, entity_ref TEXT NOT NULL,
            base_version TEXT NOT NULL, effective_from TEXT NOT NULL,
            diff TEXT NOT NULL, rationale TEXT NOT NULL, evidence_ref TEXT NOT NULL,
            schema_version TEXT NOT NULL, policy_version TEXT NOT NULL,
            source_ref TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(id,version));''')
        db.executescript('''CREATE INDEX IF NOT EXISTS change_as_code_customer ON change_as_code(customer_id,entity_type,entity_ref,version);
            CREATE TRIGGER IF NOT EXISTS change_as_code_no_update BEFORE UPDATE ON change_as_code BEGIN SELECT RAISE(ABORT,'change-as-code is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS change_as_code_no_delete BEFORE DELETE ON change_as_code BEGIN SELECT RAISE(ABORT,'change-as-code is append-only'); END;''')
        # TWIN-003 Impactanalyse
        db.executescript('''CREATE TABLE IF NOT EXISTS impact_analysis(
            id TEXT NOT NULL, version INTEGER NOT NULL,
            customer_id TEXT NOT NULL REFERENCES customers(id),
            baseline_ref TEXT NOT NULL, scenario_ref TEXT NOT NULL,
            domains TEXT NOT NULL, comparison TEXT NOT NULL,
            calc_logic_version TEXT NOT NULL, policy_version TEXT NOT NULL,
            schema_version TEXT NOT NULL, source_ref TEXT NOT NULL,
            valid_at TEXT, known_at TEXT,
            outcome TEXT, created_by TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(id,version));''')
        db.executescript('''CREATE INDEX IF NOT EXISTS impact_analysis_customer ON impact_analysis(customer_id,baseline_ref,scenario_ref,version);
            CREATE TRIGGER IF NOT EXISTS impact_analysis_no_update BEFORE UPDATE ON impact_analysis BEGIN SELECT RAISE(ABORT,'impact analysis is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS impact_analysis_no_delete BEFORE DELETE ON impact_analysis BEGIN SELECT RAISE(ABORT,'impact analysis is append-only'); END;''')

        dora_columns={r["name"] for r in db.execute("PRAGMA table_info(dora_assessments)")}
        if "effective_from" not in dora_columns: db.execute("ALTER TABLE dora_assessments ADD COLUMN effective_from TEXT")
        if "effective_to" not in dora_columns: db.execute("ALTER TABLE dora_assessments ADD COLUMN effective_to TEXT")
        config_columns={r["name"] for r in db.execute("PRAGMA table_info(config_versions)")}
        if "schema_version" not in config_columns: db.execute("ALTER TABLE config_versions ADD COLUMN schema_version TEXT NOT NULL DEFAULT '1'")
        change_columns={r["name"] for r in db.execute("PRAGMA table_info(change_sets)")}
        if "schema_version" not in change_columns: db.execute("ALTER TABLE change_sets ADD COLUMN schema_version TEXT NOT NULL DEFAULT '1'")
        # BENCH-002: bitemporele benchmarkvelden migreren (add-only, geen verwijdering).
        bench_columns={r["name"] for r in db.execute("PRAGMA table_info(benchmark_versions)")}
        for col in ("effective_date","history_policy","known_at","valid_from","valid_to"):
            if col not in bench_columns: db.execute(f"ALTER TABLE benchmark_versions ADD COLUMN {col} TEXT")
        # AUD-001: audit-uitbreidingen append-only migreren (add-only, geen verwijdering).
        audit_columns={r["name"] for r in db.execute("PRAGMA table_info(audit)")}
        for col,ddl in (("old_value","TEXT"),("new_value","TEXT"),("evidence","TEXT"),("policy_version","TEXT"),("schema_version","TEXT"),("simulation","TEXT"),("approval","TEXT"),("activation","TEXT"),("publication_status","TEXT")):
            if col not in audit_columns: db.execute(f"ALTER TABLE audit ADD COLUMN {col} {ddl}")
        seed_configuration_schemas(db)
        if not db.execute("SELECT 1 FROM customers LIMIT 1").fetchone(): seed(db)
        if not db.execute("SELECT 1 FROM policy_controls LIMIT 1").fetchone(): seed_policies(db)
        for row in db.execute("SELECT id FROM customers").fetchall():
            if not db.execute("SELECT 1 FROM config_knowledge_snapshots WHERE customer_id=? LIMIT 1",(row["id"],)).fetchone():
                snapshot_config_knowledge(db,row["id"],"system.migration","Initiële snapshot bij ingebruikname bitemporele historie",now())
            if not db.execute("SELECT 1 FROM graph_knowledge_snapshots WHERE customer_id=? LIMIT 1",(row["id"],)).fetchone():
                snapshot_graph_knowledge(db,row["id"],"system.migration","Initiële graafsnapshot bij ingebruikname bitemporele historie",now())
            latest=db.execute("SELECT timeline FROM graph_knowledge_snapshots WHERE customer_id=? ORDER BY recorded_at DESC,revision DESC LIMIT 1",(row["id"],)).fetchone()
            if latest and "requirements" not in json.loads(latest["timeline"]):
                snapshot_graph_knowledge(db,row["id"],"system.migration","Klantvereisten-baseline; eerdere transaction-time is niet reconstrueerbaar",now())
            config_snapshot=db.execute("SELECT timeline FROM config_knowledge_snapshots WHERE customer_id=? ORDER BY recorded_at DESC,revision DESC LIMIT 1",(row["id"],)).fetchone()
            if config_snapshot and any("schema_version" not in v for v in json.loads(config_snapshot["timeline"])):
                snapshot_config_knowledge(db,row["id"],"system.migration","Configuratieschemaversie-baseline; eerdere schemaverwijzing niet reconstrueerbaar",now())

def seed_policies(db):
    samples=[
      ("CLIENT-PAI-DATA","PAI-data-aanlevering per mandaat","Compliance (te bevestigen)","Klant / mandaat / manager","Klantspecifiek contract (synthetisch voorbeeld)","Alleen indien contractueel overeengekomen en toepasselijk vastgesteld","manual","2026-11-03","2027-11-03","pending","Nog te valideren door Compliance/Legal; geen generieke SFDR-claim."),
      ("WTP-TRANSITION-DATA","Wtp-transitiedata en mijlpalen","Client Service (te bevestigen)","Pensioenfonds / vermogensbeheerketen","Klantafspraak (synthetisch voorbeeld)","Per fonds en transitiefase te bepalen","manual","2026-11-03","2027-11-03","pending","Data-eisen en verantwoordelijkheden zijn klantspecifiek; te valideren."),
      ("ICT-DORA-SCOPE","Classificatie ICT- en vermogensbeheerdienst","Compliance (te bevestigen)","Dienstverlener / contract","DNB-bron en klantcontract; toepasselijkheid te beoordelen","Classificeer ICT-dienst apart van vermogensbeheeractiviteit","manual","2026-11-03","2027-11-03","pending","Voorbeeldregisteritem; toepasselijkheid nog niet goedgekeurd."),
    ]
    for code,title,owner,audience,source,applies,enforcement,effective,review,status,evidence in samples:
        db.execute("INSERT INTO policy_controls VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(str(uuid.uuid4()),code,1,title,owner,audience,source,applies,enforcement,effective,review,status,evidence,"system.seed",now(),"Synthetisch voorbeeld; niet-gevalideerd."))

def _utc_stamp(value):
    parsed=datetime.fromisoformat(value.replace("Z","+00:00"))
    if parsed.tzinfo is None: parsed=parsed.replace(tzinfo=timezone.utc)
    # Browser datetime-local inputs may omit seconds. Treat the selected
    # precision as inclusive so subsecond audit timestamps in that second or minute match.
    timepart=value.split("T",1)[1].split("Z",1)[0].split("+",1)[0]
    if len(timepart)==5: parsed=parsed.replace(second=59,microsecond=999999)
    elif "T" in value and "." not in timepart: parsed=parsed.replace(microsecond=999999)
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds")

def seed_configuration_schemas(db):
    for version,schema in config_schema.schema_versions():
        serialized=json.dumps(schema,sort_keys=True,separators=(",",":"))
        existing=db.execute("SELECT schema_json FROM config_schema_versions WHERE version=?",(version,)).fetchone()
        if existing:
            if existing["schema_json"]!=serialized:
                raise ValueError(f"Configuratieschema v{version} is onveranderlijk; publiceer een nieuwe versie")
            continue
        prior=db.execute("SELECT MAX(version) FROM config_schema_versions").fetchone()[0] or 0
        if version!=prior+1: raise ValueError(f"Schemaversie moet append-only opvolgen: verwacht v{prior+1}, kreeg v{version}")
        stamp=now(); actor="system.schema-bootstrap"; rationale=f"Versie uit {schema['$id']} geregistreerd"
        db.execute("INSERT INTO config_schema_versions VALUES(?,?,?,?,?,?,?,?,?)",(version,schema["$id"],schema["title"],schema["x-owner"],schema["x-effective-from"],stamp,serialized,actor,rationale))
        audit(db,"configuration_schema",schema["$id"],"registered",actor,rationale,{"version":version,"effective_from":schema["x-effective-from"]})

def configuration_schemas():
    with connect() as db: rows=db.execute("SELECT version,schema_id,title,owner,effective_from,recorded_at,schema_json FROM config_schema_versions ORDER BY version ASC").fetchall()
    return [{"version":str(r["version"]),"id":r["schema_id"],"title":r["title"],"owner":r["owner"],"effective_from":r["effective_from"],"recorded_at":r["recorded_at"],"parameters":config_schema.parameter_definitions(json.loads(r["schema_json"]))} for r in rows]

def configuration_schema(version=None,valid_at=None,known_at=None):
    known_stamp=_utc_stamp(known_at or now()); valid_at=valid_at or datetime.now(timezone.utc).date().isoformat()
    with connect() as db:
        if version is not None: row=db.execute("SELECT * FROM config_schema_versions WHERE version=? AND recorded_at<=?",(int(version),known_stamp)).fetchone()
        else: row=db.execute("SELECT * FROM config_schema_versions WHERE effective_from<=? AND recorded_at<=? ORDER BY version DESC LIMIT 1",(valid_at,known_stamp)).fetchone()
    if not row: raise ValueError(f"Geen configuratieschema beschikbaar voor valid_at={valid_at} en known_at={known_stamp}")
    result=dict(row); result["schema"]=json.loads(result.pop("schema_json")); return result

def validate_configuration(configuration,version=None):
    record=configuration_schema(version); schema=record["schema"]; errors=config_schema.validate(configuration,schema)
    return {"valid":not errors,"schema_version":str(record["version"]),"errors":errors,"parameters":config_schema.parameter_definitions(schema)}

def audit_configuration_validation(configuration,result,actor,reason):
    fingerprint=hashlib.sha256(json.dumps(configuration,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    with connect() as db:
        audit(db,"configuration_schema",f"configuration-v{result['schema_version']}","validated",actor,reason,{"schema_version":result["schema_version"],"valid":result["valid"],"error_count":len(result["errors"]),"configuration_sha256":fingerprint})

def customer(cid,valid_at=None,known_at=None):
    valid_at=valid_at or datetime.now(timezone.utc).date().isoformat(); known_at=_utc_stamp(known_at or now())
    with connect() as db:
        base=db.execute("SELECT * FROM customers WHERE id=?",(cid,)).fetchone()
        if not base:return None
        snapshot=db.execute("SELECT * FROM config_knowledge_snapshots WHERE customer_id=? AND recorded_at<=? ORDER BY recorded_at DESC,revision DESC LIMIT 1",(cid,known_at)).fetchone()
        if snapshot:
            timeline=json.loads(snapshot["timeline"])
            item=next((v for v in timeline if v["valid_from"]<=valid_at and (v["valid_to"] is None or v["valid_to"]>valid_at)),None)
            if not item:return None
            return {**dict(base),**item,"schema_version":item.get("schema_version","1"),"recorded_from":snapshot["recorded_at"],"recorded_to":None,"payload":item["payload"],"snapshot_revision":snapshot["revision"],"known_at":snapshot["recorded_at"],"valid_at":valid_at}
        # Preserve legacy reads for timestamps predating the first snapshot.
        row=db.execute('''SELECT c.*,v.version,v.valid_from,v.valid_to,v.recorded_from,v.recorded_to,v.payload,v.schema_version FROM customers c JOIN config_versions v ON c.id=v.customer_id WHERE c.id=? AND v.valid_from<=? AND (v.valid_to IS NULL OR v.valid_to>?) AND v.recorded_from<=? AND (v.recorded_to IS NULL OR v.recorded_to>?) ORDER BY v.version DESC LIMIT 1''',(cid,valid_at,valid_at,known_at,known_at)).fetchone()
        if not row:return None
        out=dict(row);out["payload"]=json.loads(row["payload"]);return out

def snapshot_config_knowledge(db,cid,actor,reason,stamp=None):
    stamp=stamp or now()
    rows=db.execute("SELECT version,valid_from,valid_to,payload,change_id,schema_version FROM config_versions WHERE customer_id=? AND recorded_to IS NULL ORDER BY valid_from,version",(cid,)).fetchall()
    timeline=[{"version":r["version"],"valid_from":r["valid_from"],"valid_to":r["valid_to"],"payload":json.loads(r["payload"]),"change_id":r["change_id"],"schema_version":r["schema_version"]} for r in rows]
    revision=db.execute("SELECT COALESCE(MAX(revision),0)+1 FROM config_knowledge_snapshots WHERE customer_id=?",(cid,)).fetchone()[0]
    db.execute("INSERT INTO config_knowledge_snapshots VALUES(?,?,?,?,?,?,?)",(str(uuid.uuid4()),cid,revision,stamp,actor,reason,json.dumps(timeline,sort_keys=True)))
    audit(db,"config_knowledge",cid,"snapshot_captured",actor,reason,{"revision":revision,"recorded_at":stamp,"segments":len(timeline)})
    return revision

def config_knowledge_history(cid):
    with connect() as db: rows=db.execute("SELECT revision,recorded_at,actor,reason,timeline FROM config_knowledge_snapshots WHERE customer_id=? ORDER BY revision DESC",(cid,)).fetchall()
    return [{"revision":r["revision"],"recorded_at":r["recorded_at"],"actor":r["actor"],"reason":r["reason"],"segments":[{k:v.get(k,"1" if k=="schema_version" else None) for k in ("version","valid_from","valid_to","change_id","schema_version")} for v in json.loads(r["timeline"])]} for r in rows]

def customers():
    with connect() as db: ids=db.execute("SELECT id FROM customers ORDER BY name").fetchall()
    return [customer(r["id"]) for r in ids]

def audit(db,typ,eid,action,actor,reason,details,old_value=None,new_value=None,evidence=None,policy_version=None,schema_version=None,simulation=None,approval=None,activation=None,publication_status=None):
    """AUD-001: append-only auditlegging — actor, actie, tijd, oude/nieuwe waarde,
    reden, bronbewijs, policy-/schema-versie, simulatie, goedkeuring, activatie
    en export/publicatiestatus. Geen updates of deletes: zie audit_no_update/audit_no_delete."""
    dump=lambda v: json.dumps(v) if isinstance(v,(dict,list)) else v
    db.execute("INSERT INTO audit(entity_type,entity_id,action,actor,reason,at,details,old_value,new_value,evidence,policy_version,schema_version,simulation,approval,activation,publication_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (typ,eid,action,actor,reason,now(),json.dumps(details),dump(old_value),dump(new_value),evidence,policy_version,schema_version,dump(simulation),dump(approval),dump(activation),publication_status))
def change(cid):
    with connect() as db: row=db.execute("SELECT * FROM change_sets WHERE id=?",(cid,)).fetchone()
    if not row:return None
    out=dict(row)
    for k in ("patch","simulation"): out[k]=json.loads(out[k]) if out[k] else None
    return out
def list_changes():
    with connect() as db: rows=db.execute("SELECT id FROM change_sets ORDER BY created_at DESC").fetchall()
    return [change(r["id"]) for r in rows]
def create_change(d):
    base=customer(d["customer_id"],d["effective_date"])
    if not base: raise ValueError("Klantconfiguratie niet gevonden op ingangsdatum")
    if base["version"]!=int(d.get("base_version",base["version"])): raise ValueError("Basisversie verouderd; laad opnieuw")
    patch=d.get("patch")
    if not isinstance(patch,dict) or not patch: raise ValueError("Change-set bevat geen wijzigingen")
    allowed={"fees.bps","fees.minimum_eur","fees.frequency","mandate.benchmark","mandate.delegation","sla.target_percent","reporting.frequency","reporting.deadline_business_days","services"}
    candidate=json.loads(json.dumps(base["payload"]))
    for path,value in patch.items():
        if path not in allowed: raise ValueError(f"Niet-ondersteund configuratiepad: {path}")
        if path=="fees.bps" and not 0<=float(value)<=1000: raise ValueError("Fee bps moet tussen 0 en 1000 liggen")
        keys=path.split("."); target=candidate
        for key in keys[:-1]: target=target[int(key)] if isinstance(target,list) else target[key]
        if isinstance(target,list) and keys[-1].isdigit(): target[int(keys[-1])]=value
        elif isinstance(target,dict): target[keys[-1]]=value
        else: raise ValueError(f"Configuratiepad kan niet worden gewijzigd: {path}")
    schema_version=str(configuration_schema(valid_at=d["effective_date"])["version"])
    validation=validate_configuration(candidate,schema_version)
    if not validation["valid"]: raise ValueError("Configuratie voldoet niet aan schema v"+validation["schema_version"]+": "+"; ".join(f"{e['path']}: {e['message']}" for e in validation["errors"]))
    cid=str(uuid.uuid4()); actor=d.get("actor","demo.user"); reason=d.get("rationale","").strip()
    if not reason: raise ValueError("Onderbouwing is verplicht")
    with connect() as db:
        db.execute("INSERT INTO change_sets(id,title,customer_id,base_version,patch,effective_date,rationale,status,created_by,created_at,simulation,approved_by,approved_at,activated_at,schema_version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(cid,d.get("title") or "Configuratiewijziging",d["customer_id"],base["version"],json.dumps(patch),d["effective_date"],reason,"draft",actor,now(),None,None,None,None,schema_version))
        old_values={p:None for p in patch}
        for p in patch:
            keys=p.split("."); cur=json.loads(json.dumps(base["payload"]))
            try:
                for k in keys[:-1]: cur=cur[int(k)] if isinstance(cur,list) else cur[k]
                old_values[p]=cur[int(keys[-1])] if isinstance(cur,list) and keys[-1].isdigit() else cur[keys[-1]]
            except (KeyError,IndexError,TypeError,ValueError): old_values[p]=None
        audit(db,"change_set",cid,"created",actor,reason,{"base_version":base["version"],"patch":patch,"schema_version":schema_version},old_value=old_values,new_value=patch,evidence=reason,schema_version=schema_version)
    return change(cid)
def simulate(cid,inputs):
    item=change(cid)
    if not item:raise ValueError("Change-set niet gevonden")
    base=customer(item["customer_id"],item["effective_date"]); p=item["patch"]; payload=base["payload"]
    aum=float(inputs.get("aum_eur",250_000_000)); old=payload["fees"]["bps"]; new=p.get("fees.bps",old)
    result={"as_of":item["effective_date"],"baseline_version":item["base_version"],"schema_version":item.get("schema_version",base.get("schema_version","1")),"annual_fee_baseline_eur":round(aum*old/10000,2),"annual_fee_scenario_eur":round(aum*float(new)/10000,2),"annual_fee_delta_eur":fee_delta(aum,old,new)/100,"aum_input_eur":aum,"assumptions":["AUM is handmatige scenario-input","Annualized; tiers, minimum fee, FX and performance fees excluded in this MVP"],"operational":["Rapportage- en capaciteitseffecten zijn nog niet doorgerekend"],"compliance":[{"severity":"review","code":"HUMAN_REVIEW_REQUIRED","message":"Beoordeel klantimpact, eerlijke behandeling en toepasselijke beleidsregels; te valideren door Compliance/Legal."}],"affected":["Klantconfiguratie","Mandaat fees" if new!=old else "Mandaat"],"reproducibility":{"engine":"domain-v1","input":{"aum_eur":aum},"change_set":cid}}
    with connect() as db:
        db.execute("UPDATE change_sets SET simulation=?,status='simulated' WHERE id=?",(json.dumps(result),cid)); audit(db,"change_set",cid,"simulated",inputs.get("actor","demo.user"),"Impactanalyse",result,simulation=result,schema_version=result.get("schema_version"),evidence="change_set simulation engine domain-v1")
    return result
def approve(cid,d):
    item=change(cid)
    if not item or item["status"]!="simulated" or not item["simulation"]:raise ValueError("Eerst een simulatie uitvoeren")
    actor=d.get("actor","demo.approver")
    if actor==item["created_by"]:raise ValueError("Initiator kan niet zelf goedkeuren (vier-ogen-principe)")
    with connect() as db:
        db.execute("UPDATE change_sets SET status='approved',approved_by=?,approved_at=? WHERE id=?",(actor,now(),cid)); audit(db,"change_set",cid,"approved",actor,d.get("reason","Goedgekeurd"),{"simulation":item["simulation"]},approval={"approved_by":actor,"approved_at":now()},simulation=item["simulation"],schema_version=item.get("schema_version"),evidence=d.get("evidence") or d.get("reason","Goedgekeurd"))
    return change(cid)
def activate(cid,d):
    item=change(cid)
    if not item or item["status"]!="approved":raise ValueError("Alleen goedgekeurde wijzigingssets kunnen worden geactiveerd")
    stamp=now()
    with connect() as db:
        old=db.execute("SELECT * FROM config_versions WHERE customer_id=? AND recorded_to IS NULL ORDER BY version DESC LIMIT 1",(item["customer_id"],)).fetchone()
        if old["version"]!=item["base_version"]:raise ValueError("Basisconfiguratie gewijzigd; maak een nieuwe simulatie")
        payload=json.loads(old["payload"])
        for path,value in item["patch"].items():
            keys=path.split("."); cur=payload
            for key in keys[:-1]:cur=cur[key]
            cur[keys[-1]]=value
        if old["valid_from"] < item["effective_date"]:
            # A future-effective change must leave the former valid-time interval
            # readable at the present transaction time.
            db.execute("UPDATE config_versions SET valid_to=? WHERE id=?",(item["effective_date"],old["id"]))
        else:
            # A retroactive correction closes what we previously knew, while the
            # replacement records the corrected knowledge from this timestamp.
            db.execute("UPDATE config_versions SET recorded_to=? WHERE id=?",(stamp,old["id"]))
        schema_version=str(item.get("schema_version",old["schema_version"]))
        validation=validate_configuration(payload,schema_version)
        if not validation["valid"]: raise ValueError("Configuratie voldoet niet aan schema v"+schema_version+": "+"; ".join(f"{e['path']}: {e['message']}" for e in validation["errors"]))
        db.execute("INSERT INTO config_versions(id,customer_id,version,valid_from,valid_to,recorded_from,recorded_to,payload,change_id,schema_version) VALUES(?,?,?,?,?,?,?,?,?,?)",(str(uuid.uuid4()),item["customer_id"],old["version"]+1,item["effective_date"],old["valid_to"],stamp,None,json.dumps(payload),cid,schema_version))
        db.execute("UPDATE change_sets SET status='active',activated_at=? WHERE id=?",(stamp,cid)); audit(db,"change_set",cid,"activated",d.get("actor","demo.operator"),d.get("reason","Geactiveerd"),{"new_version":old["version"]+1,"schema_version":schema_version},activation={"new_version":old["version"]+1,"activated_at":stamp},schema_version=schema_version,evidence=d.get("evidence") or d.get("reason","Geactiveerd"))
        snapshot_config_knowledge(db,item["customer_id"],d.get("actor","demo.operator"),d.get("reason","Geactiveerd"),stamp)
    return change(cid)
def profiles():
    with connect() as db: rows=db.execute("SELECT * FROM partner_profiles ORDER BY name").fetchall()
    return [{**dict(r),"mapping":json.loads(r["mapping"])} for r in rows]
def export_config(cid,profile_id,actor="demo.publisher",valid_at=None):
    cfg=customer(cid,valid_at)
    if not cfg:raise ValueError("Geen configuratie gevonden")
    validation=validate_configuration(cfg["payload"],cfg.get("schema_version","1"))
    if not validation["valid"]:raise ValueError("Configuratie voldoet niet aan schema v"+validation["schema_version"]+": "+"; ".join(f"{e['path']}: {e['message']}" for e in validation["errors"]))
    with connect() as db: profile=db.execute("SELECT * FROM partner_profiles WHERE id=?",(profile_id,)).fetchone()
    if not profile:raise ValueError("Partnerprofiel niet gevonden")
    body={"metadata":{"customer_id":cid,"config_version":cfg["version"],"configuration_schema_version":cfg.get("schema_version","1"),"schema_version":profile["schema_version"],"profile":profile_id,"generated_at":now()},"configuration":{"customer":{"name":cfg["name"],"type":cfg["kind"],"jurisdiction":cfg["jurisdiction"]},**cfg["payload"]}}
    serialized=json.dumps(body,sort_keys=True,separators=(",",":")); checksum=hashlib.sha256(serialized.encode()).hexdigest(); eid=str(uuid.uuid4())
    with connect() as db:
        db.execute("INSERT INTO exports VALUES(?,?,?,?,?,?,?,?,?,?)",(eid,cid,cfg["version"],profile_id,profile["schema_version"],checksum,serialized,"generated",actor,now())); audit(db,"export",eid,"generated",actor,"Partnerconfiguratie-export",{"customer_id":cid,"profile":profile_id,"checksum":checksum},publication_status="generated",evidence=checksum,schema_version=profile["schema_version"])
    return {"export_id":eid,"checksum":checksum,"filename":f"{cid}-v{cfg['version']}-{eid[:8]}.json","payload":body}
def audit_log(limit=100):
    with connect() as db: rows=db.execute("SELECT * FROM audit ORDER BY at DESC LIMIT ?",(limit,)).fetchall()
    out=[]
    for r in rows:
        row={**dict(r),"details":json.loads(r["details"])}
        for k in ("old_value","new_value","simulation","approval","activation"):
            if isinstance(row.get(k),str):
                try: row[k]=json.loads(row[k])
                except ValueError: pass
        out.append(row)
    return out

def _config_value(payload,path):
    if not path:return None
    value=payload
    try:
        for key in path.split("."):
            value=value[int(key)] if isinstance(value,list) else value[key]
        return value
    except (KeyError,IndexError,TypeError,ValueError):return None

def client_requirements(customer_id=None, valid_at=None, known_at=None):
    with connect() as db:
        if customer_id and valid_at and known_at:
            snapshot=db.execute("SELECT timeline FROM graph_knowledge_snapshots WHERE customer_id=? AND recorded_at<=? ORDER BY recorded_at DESC,revision DESC LIMIT 1",(customer_id,_utc_stamp(known_at))).fetchone()
            timeline=json.loads(snapshot["timeline"]) if snapshot else {"requirements":[]}
            candidates=[r for r in timeline.get("requirements",[]) if r["effective_date"]<=valid_at]
            latest_by_id={}
            for requirement in candidates:
                prior=latest_by_id.get(requirement["id"])
                if not prior or (requirement["effective_date"],requirement["version"])>(prior["effective_date"],prior["version"]):
                    latest_by_id[requirement["id"]]=requirement
            rows=sorted(latest_by_id.values(),key=lambda r:(r["effective_date"],r["created_at"]),reverse=True)
        elif customer_id:
            rows=db.execute('''SELECT r.* FROM client_requirements r JOIN
              (SELECT id,MAX(version) version FROM client_requirements WHERE customer_id=? GROUP BY id) latest
              ON r.id=latest.id AND r.version=latest.version ORDER BY r.created_at DESC''',(customer_id,)).fetchall()
        else:
            rows=db.execute('''SELECT r.* FROM client_requirements r JOIN
              (SELECT id,MAX(version) version FROM client_requirements GROUP BY id) latest
              ON r.id=latest.id AND r.version=latest.version ORDER BY r.created_at DESC''').fetchall()
    result=[]
    for row in rows:
        item=dict(row); cfg=customer(item["customer_id"],valid_at or item["effective_date"],known_at); actual=_config_value(cfg["payload"],item["config_path"]) if cfg else None
        item["actual_value"]=actual
        item["reconciliation"]="manual_review" if not item["config_path"] else ("unmapped" if actual is None else ("configured_match" if str(actual)==str(item["expected_value"]) else "configuration_gap"))
        result.append(item)
    return result

def save_client_requirement(data):
    required=("customer_id","category","title","requirement","source_ref","frequency","effective_date","review_date","rationale")
    for key in required:
        if not str(data.get(key,"")).strip():raise ValueError(f"{key} is verplicht")
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",data["effective_date"]) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",data["review_date"]):raise ValueError
        date.fromisoformat(data["effective_date"]); date.fromisoformat(data["review_date"])
    except ValueError:raise ValueError("Geldigheids- en reviewdatum moeten ISO-formaat YYYY-MM-DD hebben")
    if not customer(data["customer_id"]):raise ValueError("Klant niet gevonden")
    allowed={"esg","sfdr_pai","wtp","reporting","disclosure","costs","chain","outsourcing"}
    category=data["category"]
    if category not in allowed:raise ValueError("Ongeldige categorie")
    req_id=data.get("id") or str(uuid.uuid4()); actor=data.get("actor","demo.client-service").strip(); stamp=now()
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM client_requirements WHERE id=? AND customer_id=?",(req_id,data["customer_id"])).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("INSERT INTO client_requirements VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(req_id,version,data["customer_id"],category,data["title"].strip(),data["requirement"].strip(),data["source_ref"].strip(),(data.get("config_path") or "").strip() or None,(data.get("expected_value") or "").strip() or None,data["frequency"].strip(),data["effective_date"],data["review_date"],actor,stamp,data["rationale"].strip()))
        audit(db,"client_requirement",req_id,"created" if version==1 else "versioned",actor,data["rationale"],{"customer_id":data["customer_id"],"version":version,"category":category,"source_ref":data["source_ref"].strip()})
        snapshot_graph_knowledge(db,data["customer_id"],actor,data["rationale"],stamp)
    return next(r for r in client_requirements(data["customer_id"]) if r["id"]==req_id)

def dora_assessments(valid_at=None, known_at=None, customer_id=None):
    known_at=_utc_stamp(known_at or now())
    with connect() as db:
        rows=db.execute("""SELECT d.* FROM dora_assessments d JOIN
          (SELECT id,MAX(version) version FROM dora_assessments WHERE created_at<=? GROUP BY id) latest
          ON d.id=latest.id AND d.version=latest.version
          WHERE (? IS NULL OR d.customer_id=? OR d.customer_id IS NULL) ORDER BY d.created_at DESC""",(known_at,customer_id,customer_id)).fetchall()
    result=[]
    for row in rows:
        item=dict(row)
        if not item["effective_from"]: item["validity_status"]="unset_legacy"
        elif valid_at and item["effective_from"]<=valid_at and (not item["effective_to"] or item["effective_to"]>valid_at): item["validity_status"]="valid"
        elif valid_at: continue
        else: item["validity_status"]="dated"
        result.append(item)
    return result

def save_dora_assessment(data):
    required=("assessment_type","counterparty","service_name","scope_description","applicability","criticality","contract_ref","source_ref","reviewer","reviewer_role","rationale","review_date","effective_from")
    for key in required:
        if not str(data.get(key,"")).strip():raise ValueError(f"{key} is verplicht")
    kinds={"managed_activity","supplier_ict","platform_ict"}
    applicability={"pending_review","in_scope","out_of_scope"}
    criticality={"unassessed","critical_important","other"}
    if data["assessment_type"] not in kinds:raise ValueError("Ongeldig classificatietype")
    if data["applicability"] not in applicability:raise ValueError("Ongeldige toepasselijkheidsstatus")
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",data["effective_from"]):raise ValueError
        date.fromisoformat(data["effective_from"])
        effective_to=(data.get("effective_to") or "").strip() or None
        if effective_to and (not re.fullmatch(r"\d{4}-\d{2}-\d{2}",effective_to) or date.fromisoformat(effective_to)<=date.fromisoformat(data["effective_from"])):raise ValueError
    except ValueError:raise ValueError("Geldigheidsperiode moet ISO YYYY-MM-DD zijn; einddatum moet na startdatum liggen")
    if data["criticality"] not in criticality:raise ValueError("Ongeldige kritikaliteitsstatus")
    customer_id=(data.get("customer_id") or "").strip() or None
    if customer_id and not customer(customer_id):raise ValueError("Klant niet gevonden")
    role=data["reviewer_role"]
    if role not in {"compliance","legal","risk","ict_risk"}:raise ValueError("Reviewerrol moet Compliance, Legal, Risk of ICT-risk zijn")
    assessment_id=data.get("id") or str(uuid.uuid4()); actor=data.get("actor",data["reviewer"]).strip(); stamp=now()
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM dora_assessments WHERE id=?",(assessment_id,)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("INSERT INTO dora_assessments(id,version,assessment_type,customer_id,counterparty,service_name,scope_description,applicability,criticality,contract_ref,source_ref,reviewer,reviewer_role,rationale,review_date,created_at,effective_from,effective_to) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(assessment_id,version,data["assessment_type"],customer_id,data["counterparty"].strip(),data["service_name"].strip(),data["scope_description"].strip(),data["applicability"],data["criticality"],data["contract_ref"].strip(),data["source_ref"].strip(),data["reviewer"].strip(),role,data["rationale"].strip(),data["review_date"],stamp,data["effective_from"],effective_to))
        audit(db,"dora_assessment",assessment_id,"created" if version==1 else "versioned",actor,data["rationale"],{"version":version,"assessment_type":data["assessment_type"],"customer_id":customer_id,"applicability":data["applicability"],"criticality":data["criticality"],"source_ref":data["source_ref"].strip(),"effective_from":data["effective_from"],"effective_to":effective_to})
    return next(r for r in dora_assessments() if r["id"]==assessment_id)

def ict_provider_relations(valid_at=None, known_at=None, customer_id=None):
    known_at=_utc_stamp(known_at or now())
    with connect() as db:
        rows=db.execute("""SELECT i.* FROM ict_provider_relations i JOIN
          (SELECT id,MAX(version) version FROM ict_provider_relations WHERE created_at<=? GROUP BY id) latest
          ON i.id=latest.id AND i.version=latest.version
          WHERE (? IS NULL OR i.customer_id=? OR i.customer_id IS NULL) ORDER BY i.created_at DESC""",(known_at,customer_id,customer_id)).fetchall()
    result=[]
    for row in rows:
        item=dict(row)
        if not item["effective_from"]: item["validity_status"]="unset_legacy"
        elif valid_at and item["effective_from"]<=valid_at and (not item["effective_to"] or item["effective_to"]>valid_at): item["validity_status"]="valid"
        elif valid_at: continue
        else: item["validity_status"]="dated"
        result.append(item)
    return result

def save_ict_provider_relation(data):
    required=("provider","ict_service","function_classification","contract_ref","incident_evidence","exit_evidence","applicability","source_ref","reviewer","reviewer_role","rationale","review_date","effective_from")
    for key in required:
        if not str(data.get(key,"")).strip():raise ValueError(f"{key} is verplicht")
    function_classification={"critical","important","other"}
    applicability={"pending_review","in_scope","out_of_scope"}
    if data["function_classification"] not in function_classification:raise ValueError("Ongeldige functieclassificatie")
    if data["applicability"] not in applicability:raise ValueError("Ongeldige toepasselijkheidsstatus")
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",data["effective_from"]):raise ValueError
        date.fromisoformat(data["effective_from"])
        effective_to=(data.get("effective_to") or "").strip() or None
        if effective_to and (not re.fullmatch(r"\d{4}-\d{2}-\d{2}",effective_to) or date.fromisoformat(effective_to)<=date.fromisoformat(data["effective_from"])):raise ValueError
    except ValueError:raise ValueError("Geldigheidsperiode moet ISO YYYY-MM-DD zijn; einddatum moet na startdatum liggen")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",data["review_date"]):raise ValueError("Geldigheids- en reviewdatum moeten ISO-formaat YYYY-MM-DD hebben")
    date.fromisoformat(data["review_date"])
    customer_id=(data.get("customer_id") or "").strip() or None
    if customer_id and not customer(customer_id):raise ValueError("Klant niet gevonden")
    role=data["reviewer_role"]
    if role not in {"compliance","legal","risk","ict_risk"}:raise ValueError("Reviewerrol moet Compliance, Legal, Risk of ICT-risk zijn")
    rid=data.get("id") or str(uuid.uuid4()); actor=data.get("actor",data["reviewer"]).strip(); stamp=now()
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM ict_provider_relations WHERE id=?",(rid,)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("INSERT INTO ict_provider_relations(id,version,customer_id,provider,ict_service,function_classification,contract_ref,incident_evidence,exit_evidence,applicability,source_ref,reviewer,reviewer_role,rationale,review_date,created_at,effective_from,effective_to) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(rid,version,customer_id,data["provider"].strip(),data["ict_service"].strip(),data["function_classification"],data["contract_ref"].strip(),data["incident_evidence"].strip(),data["exit_evidence"].strip(),data["applicability"],data["source_ref"].strip(),data["reviewer"].strip(),role,data["rationale"].strip(),data["review_date"],stamp,data["effective_from"],effective_to))
        audit(db,"ict_provider_relation",rid,"created" if version==1 else "versioned",actor,data["rationale"],{"version":version,"function_classification":data["function_classification"],"customer_id":customer_id,"applicability":data["applicability"],"source_ref":data["source_ref"].strip(),"effective_from":data["effective_from"],"effective_to":effective_to})
    return next(r for r in ict_provider_relations() if r["id"]==rid)

def governance_policies(valid_at=None, known_at=None, customer_id=None):
    known_at=_utc_stamp(known_at or now())
    with connect() as db:
        rows=db.execute("""SELECT g.* FROM governance_policies g JOIN
          (SELECT id,MAX(version) version FROM governance_policies WHERE created_at<=? GROUP BY id) latest
          ON g.id=latest.id AND g.version=latest.version
          WHERE (? IS NULL OR g.customer_id=? OR g.customer_id IS NULL) ORDER BY g.created_at DESC""",(known_at,customer_id,customer_id)).fetchall()
    result=[]
    for row in rows:
        item=dict(row)
        if not item["effective_from"]: item["validity_status"]="unset_legacy"
        elif valid_at and item["effective_from"]<=valid_at and (not item["effective_to"] or item["effective_to"]>valid_at): item["validity_status"]="valid"
        elif valid_at: continue
        else: item["validity_status"]="dated"
        result.append(item)
    return result

def save_governance_policy(data):
    required=("policy","monitoring_frequency","reporting","escalation","independent_evaluation","capacity","evaluation_date","applicability","source_ref","reviewer","reviewer_role","rationale","review_date","effective_from")
    for key in required:
        if not str(data.get(key,"")).strip():raise ValueError(f"{key} is verplicht")
    applicability={"pending_review","in_scope","out_of_scope"}
    if data["applicability"] not in applicability:raise ValueError("Ongeldige toepasselijkheidsstatus")
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",data["effective_from"]):raise ValueError
        date.fromisoformat(data["effective_from"])
        effective_to=(data.get("effective_to") or "").strip() or None
        if effective_to and (not re.fullmatch(r"\d{4}-\d{2}-\d{2}",effective_to) or date.fromisoformat(effective_to)<=date.fromisoformat(data["effective_from"])):raise ValueError
    except ValueError:raise ValueError("Geldigheidsperiode moet ISO YYYY-MM-DD zijn; einddatum moet na startdatum liggen")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",data["review_date"]):raise ValueError("Geldigheids- en reviewdatum moeten ISO-formaat YYYY-MM-DD hebben")
    date.fromisoformat(data["review_date"])
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",data["evaluation_date"]):raise ValueError("Evaluatiedatum moet ISO-formaat YYYY-MM-DD hebben")
    date.fromisoformat(data["evaluation_date"])
    customer_id=(data.get("customer_id") or "").strip() or None
    if customer_id and not customer(customer_id):raise ValueError("Klant niet gevonden")
    role=data["reviewer_role"]
    if role not in {"compliance","legal","risk","ict_risk"}:raise ValueError("Reviewerrol moet Compliance, Legal, Risk of ICT-risk zijn")
    rid=data.get("id") or str(uuid.uuid4()); actor=data.get("actor",data["reviewer"]).strip(); stamp=now()
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM governance_policies WHERE id=?",(rid,)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("INSERT INTO governance_policies(id,version,customer_id,policy,monitoring_frequency,reporting,escalation,independent_evaluation,capacity,evaluation_date,applicability,source_ref,reviewer,reviewer_role,rationale,review_date,created_at,effective_from,effective_to) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(rid,version,customer_id,data["policy"].strip(),data["monitoring_frequency"].strip(),data["reporting"].strip(),data["escalation"].strip(),data["independent_evaluation"].strip(),data["capacity"].strip(),data["evaluation_date"],data["applicability"],data["source_ref"].strip(),data["reviewer"].strip(),role,data["rationale"].strip(),data["review_date"],stamp,data["effective_from"],effective_to))
        audit(db,"governance_policy",rid,"created" if version==1 else "versioned",actor,data["rationale"],{"version":version,"customer_id":customer_id,"applicability":data["applicability"],"source_ref":data["source_ref"].strip(),"effective_from":data["effective_from"],"effective_to":effective_to})
    return next(r for r in governance_policies() if r["id"]==rid)

# --- ESG-001 Beleidsprofiel ---
# Per klant/fonds en mandaat het geldende MVB/ESG-beleid, doelen, prioriteit (rendement/risico/
# duurzaamheid), asset-class scope, versie en bronbewijs. Append-only versieer: een wijziging is
# per definitie nieuwe versie; de impactreview toont welke managers/mandaten en rapportageprofielen
# geraakt worden.
ESG_POLICY_SUBJECT_TYPES=("fund","mandate","party")
ESG_POLICY_PRIORITIES=("return","risk","sustainability","balanced")
ESG_POLICY_IMPACT_FIELDS=("policy_framework","goals","priority","asset_class_scope","assessment_methodology","esg_rating_source","decision_thresholds")
ESG_MANAGER_SELECTION_STAGES=("onboarding","annual_review","retention_review")
ESG_FLOWDOWN_CLAUSES=("oecd_ungp","due_diligence","cooperation","reporting","incident_reporting","data_position_insight","remediation","escalation")
ESG_FLOWDOWN_TARGETS=("direct_manager","sub_manager")
ESG_DD_WORKFLOW_STEPS=("policy_systems","impact_identification","prevention_mitigation","monitoring_results","communication","remediation")
ESG_DD_IMPACT_PRIORITIES=("high","medium","low")
ESG_ENGAGEMENT_SEVERITIES=("high","medium","low")
ESG_ENGAGEMENT_PROGRESS=("open","in_progress","remediated","closed")
ESG_ENGAGEMENT_RETENTION_DECISIONS=("retain","exit","pending")
ESG_REVIEW_PERIODS=("annual","client_agreed")
ESG_REVIEW_DEVIATIONS=("none","deviation","deferral")
ESG_REVIEW_ESCALATIONS=("none","escalated")

REPORTING_TYPES=("regulatory","client","internal","pai_sfdr","wtp","dora")
REPORTING_FREQUENCIES=("monthly","quarterly","semiannual","annual","ad_hoc","event_driven")
REPORTING_LANGUAGES=("nl","en","de","fr")
SUPPLIER_ROLES=("fund","fiduciary","manager","submanager","third_party")
REPORTING_EXECUTION_STATUSES=("planned","on_track","delivered","delayed","incomplete","failed","recovered","approved")
REPORTING_ESCALATION_LEVELS=("none","client","compliance","management")
TRANSPARENCY_CONFIDENTIALITY_FLAGS=("public","confidential","restricted")
TRANSPARENCY_PUBLICATION_CONSENTS=("granted","denied","pending","not_required")

def esg_policy_profiles(valid_at=None, known_at=None, customer_id=None, fund_ref=None):
    """Laatste versie per profiel; met valid_at alleen profielen geldend op die datum (zoals governance_policies)."""
    known_at=_utc_stamp(known_at or now())
    with connect() as db:
        rows=db.execute("""SELECT g.* FROM esg_policy_profiles g JOIN
          (SELECT id,MAX(version) version FROM esg_policy_profiles WHERE created_at<=? GROUP BY id) latest
          ON g.id=latest.id AND g.version=latest.version
          WHERE (? IS NULL OR g.customer_id=?) AND (? IS NULL OR g.fund_ref=?) ORDER BY g.created_at DESC""",
          (known_at,customer_id,customer_id,fund_ref,fund_ref)).fetchall()
    result=[]
    for row in rows:
        item=dict(row)
        if not item["effective_from"]: item["validity_status"]="unset_legacy"
        elif valid_at and item["effective_from"]<=valid_at and (not item["effective_to"] or item["effective_to"]>valid_at): item["validity_status"]="valid"
        elif valid_at: continue
        else: item["validity_status"]="dated"
        result.append(item)
    return result

def esg_policy_profile_in_force(customer_id, fund_ref, subject_type=None, subject_id=None, valid_at=None, known_at=None):
    """Toepasselijke criteria zichtbaar en bewijsbaar bij manager onboarding en jaarlijkse review:
    mandaatspecifiek profiel wint van het fondsdekkende standaardprofiel; zonder eigen mandaatprofiel
    en zonder fondsdekkend standaardprofiel wordt geweigerd (ValueError) in plaats van ander beleid
    als fondsdekkend te presenteren; bronbewijs (source_ref, evidence_ref, beleidsdocumentversie)
    reist mee als evidence."""
    candidates=esg_policy_profiles(valid_at=valid_at,known_at=known_at,customer_id=customer_id,fund_ref=fund_ref)
    if not candidates: raise ValueError(f"Geen geldend ESG-beleidsprofiel voor {customer_id}/{fund_ref} op valid_at={valid_at or '*'} en known_at={known_at or '*'}")
    specific=[r for r in candidates if subject_type and subject_id and r["subject_type"]==subject_type and r["subject_id"]==subject_id]
    fund_default=[r for r in candidates if not r["subject_id"]]
    if specific: item, resolved=dict(specific[0]),"mandate_specific"
    elif fund_default: item, resolved=dict(fund_default[0]),"fund_default"
    else:
        wanted=f" voor subject {subject_type}={subject_id}" if subject_type and subject_id else ""
        raise ValueError(f"Geen fondsdekkend standaardprofiel en geen mandaatspecifiek profiel{wanted} voor {customer_id}/{fund_ref} op valid_at={valid_at or '*'} en known_at={known_at or '*'}")
    item["resolved_from"]=resolved
    item["evidence"]={"source_ref":item["source_ref"],"evidence_ref":item["evidence_ref"],
        "policy_document_version":item["policy_document_version"],
        "review_cycle":item["review_cycle"],"next_review_at":item["next_review_at"],"resolved_from":resolved}
    return item

def save_esg_policy_profile(data):
    required=("customer_id","fund_ref","subject_type","policy_framework","goals","priority",
              "asset_class_scope","effective_from","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["subject_type"] not in ESG_POLICY_SUBJECT_TYPES: raise ValueError(f"subject_type moet een van {', '.join(ESG_POLICY_SUBJECT_TYPES)} zijn")
    if data["priority"] not in ESG_POLICY_PRIORITIES: raise ValueError(f"prioriteit moet een van {', '.join(ESG_POLICY_PRIORITIES)} zijn")
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",data["effective_from"]): raise ValueError
        date.fromisoformat(data["effective_from"])
        effective_to=(data.get("effective_to") or "").strip() or None
        if effective_to and (not re.fullmatch(r"\d{4}-\d{2}-\d{2}",effective_to) or date.fromisoformat(effective_to)<=date.fromisoformat(data["effective_from"])): raise ValueError
        next_review_at=(data.get("next_review_at") or "").strip() or None
        if next_review_at:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",next_review_at): raise ValueError
            date.fromisoformat(next_review_at)
    except ValueError: raise ValueError("Geldigheids- en reviewdatum moeten ISO-formaat YYYY-MM-DD hebben; einddatum moet na de ingangsdatum liggen")
    # Standaard-id namespaced per klant/fonds/onderwerp: dezelfde natuurlijke sleutel bij een
    # andere klant mag nooit botsen op de globale PK (id,version).
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["fund_ref"]))))
    pid=data.get("id") or f"esgp-{slug}-{data['subject_type']}"+(f"-{re.sub(r'[^a-z0-9]+','-',str(data['subject_id']).lower()).strip('-')}" if data.get("subject_id") else "")
    actor=data.get("actor","demo.client-service").strip(); stamp=now(); cid=data["customer_id"]
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM esg_policy_profiles WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO esg_policy_profiles(id,version,customer_id,fund_ref,subject_type,subject_id,
          policy_framework,goals,priority,asset_class_scope,oeso_ungp_diligence,imvb_diligence,
          assessment_methodology,esg_rating_source,decision_thresholds,policy_document_version,evidence_ref,
          effective_from,effective_to,review_cycle,next_review_at,source_ref,rationale,created_by,created_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,str(data["fund_ref"]).strip(),data["subject_type"],(data.get("subject_id") or "").strip() or None,
           data["policy_framework"].strip(),data["goals"].strip(),data["priority"],data["asset_class_scope"].strip(),
           (data.get("oeso_ungp_diligence") or "").strip() or None,(data.get("imvb_diligence") or "").strip() or None,
           (data.get("assessment_methodology") or "").strip() or None,(data.get("esg_rating_source") or "").strip() or None,
           (data.get("decision_thresholds") or "").strip() or None,(data.get("policy_document_version") or "").strip() or None,
           (data.get("evidence_ref") or "").strip() or None,
           data["effective_from"],effective_to,(data.get("review_cycle") or "").strip() or None,next_review_at,
           data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"esg_policy_profile",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"fund_ref":data["fund_ref"],"subject_type":data["subject_type"],
             "subject_id":data.get("subject_id"),"priority":data["priority"],
             "asset_class_scope":data["asset_class_scope"],"source_ref":data["source_ref"].strip(),
             "effective_from":data["effective_from"],"effective_to":effective_to})
    with connect() as db: saved=db.execute("SELECT * FROM esg_policy_profiles WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def save_esg_policy_exception(data):
    """Uitzondering op het geldende beleidsprofiel: rationale, goedkeurder en einddatum zijn verplicht; append-only."""
    required=("customer_id","profile_id","description","rationale","approver","end_date")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",data["end_date"]): raise ValueError
        date.fromisoformat(data["end_date"])
        effective_from=(data.get("effective_from") or "").strip() or None
        if effective_from and (not re.fullmatch(r"\d{4}-\d{2}-\d{2}",effective_from) or date.fromisoformat(effective_from)>date.fromisoformat(data["end_date"])): raise ValueError
    except ValueError: raise ValueError("Einddatum moet een ISO-datum YYYY-MM-DD zijn en na de ingangsdatum liggen")
    cid=data["customer_id"]
    with connect() as db:
        profile=db.execute("SELECT * FROM esg_policy_profiles WHERE id=? AND customer_id=? ORDER BY version DESC",(data["profile_id"],cid)).fetchone()
        if not profile: raise ValueError("Beleidsprofiel voor deze klant niet gevonden")
        eid=data.get("id") or f"esgpe-{re.sub(r'[^a-z0-9]+','-',str(data['profile_id']).lower()).strip('-')}"
        previous=db.execute("SELECT MAX(version) version FROM esg_policy_exceptions WHERE id=? AND customer_id=?",(eid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        actor=data.get("actor",data["approver"]).strip(); stamp=now()
        fund_ref=(data.get("fund_ref") or "").strip() or profile["fund_ref"]
        subject_type=(data.get("subject_type") or "").strip() or profile["subject_type"]
        subject_id=(data.get("subject_id") or "").strip() or profile["subject_id"]
        db.execute("""INSERT INTO esg_policy_exceptions(id,version,customer_id,profile_id,fund_ref,subject_type,subject_id,
          description,rationale,approver,scope_description,effective_from,end_date,evidence_ref,source_ref,created_by,created_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (eid,version,cid,data["profile_id"],fund_ref,subject_type,subject_id,
           data["description"].strip(),data["rationale"].strip(),data["approver"].strip(),
           (data.get("scope_description") or "").strip() or None,effective_from,data["end_date"],
           (data.get("evidence_ref") or "").strip() or None,(data.get("source_ref") or "").strip() or None,actor,stamp))
        audit(db,"esg_policy_exception",eid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"profile_id":data["profile_id"],"approver":data["approver"],
             "end_date":data["end_date"]})
    with connect() as db: saved=db.execute("SELECT * FROM esg_policy_exceptions WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(eid,cid)).fetchone()
    return dict(saved)

def esg_policy_exceptions(valid_at=None, known_at=None, customer_id=None):
    """Uitzonderingen met hun geldigheid: na de einddatum markeren we de rij als expired (geen hard delete)."""
    known_at=_utc_stamp(known_at or now())
    with connect() as db:
        rows=db.execute("""SELECT e.* FROM esg_policy_exceptions e JOIN
          (SELECT id,MAX(version) version FROM esg_policy_exceptions WHERE created_at<=? GROUP BY id) latest
          ON e.id=latest.id AND e.version=latest.version
          WHERE (? IS NULL OR e.customer_id=?) ORDER BY e.created_at DESC""",(known_at,customer_id,customer_id)).fetchall()
    result=[]
    for row in rows:
        item=dict(row)
        if not valid_at: item["validity_status"]="unknown_without_valid_at"
        elif item["end_date"]<valid_at: item["validity_status"]="expired"
        else: item["validity_status"]="active"
        result.append(item)
    return result

def esg_policy_change_impact(data):
    """Wijziging van klantbeleid: toon welke managers/mandaten en rapportageprofielen geraakt worden.
    Een profiel is geraakt wanneer een aangeleverd nieuw beleidsveld afwijkt van de waarde in het
    in-kracht-profiel (afwijkende mandaten moeten herbeoordeeld of expliciet geünificeerd als
    uitzondering); rapportageprofielen = rapportagevereisten van de klant + exportprofielen in gebruik."""
    for key in ("customer_id",):
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    provided=[f for f in ESG_POLICY_IMPACT_FIELDS if str(data.get(f,"")).strip()]
    if not provided: raise ValueError(f"Minimaal één nieuw beleidsveld is verplicht: {', '.join(ESG_POLICY_IMPACT_FIELDS)}")
    cid=data["customer_id"]
    if not customer(cid): raise ValueError("Klant niet gevonden")
    actor=data.get("actor","demo.client-service").strip()
    profiles=esg_policy_profiles(customer_id=cid,valid_at=data.get("valid_at"))
    affected=[]; mandates=[]
    for profile in profiles:
        changed=[f for f in provided if profile.get(f)!=data[f].strip()]
        if changed:
            affected.append({"id":profile["id"],"version":profile["version"],"fund_ref":profile["fund_ref"],
                "subject_type":profile["subject_type"],"subject_id":profile["subject_id"],"changed_fields":changed})
            if profile["subject_id"]: mandates.append({"fund_ref":profile["fund_ref"],"subject_type":profile["subject_type"],"subject_id":profile["subject_id"]})
    requirements=client_requirements(cid)
    affected_reporting=[dict(r) for r in requirements if r["category"]=="reporting"]
    with connect() as db:
        export_profile_refs=[r["profile_id"] for r in db.execute("SELECT DISTINCT profile_id FROM exports WHERE customer_id=?",(cid,)).fetchall()]
    with connect() as db:
        audit(db,"esg_policy_profile",cid,"impact_reviewed",actor,data.get("rationale") or "beleidswijziging-impactreview",
            {"customer_id":cid,"provided_fields":provided,"affected_profiles":len(affected),
             "affected_reporting_requirements":len(affected_reporting),"affected_export_profiles":len(export_profile_refs)})
    return {"customer_id":cid,"proposed":{f:data[f].strip() for f in provided},
        "affected_profiles":affected,"affected_managers_mandates":mandates,
        "affected_reporting_requirements":affected_reporting,
        "affected_partner_export_profiles":export_profile_refs,
        "unaffected_profile_count":len(profiles)-len(affected)}

def save_esg_manager_selection(data):
    required=("customer_id","fund_ref","manager_ref","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    stage=data.get("selection_stage") or "onboarding"
    if stage not in ESG_MANAGER_SELECTION_STAGES: raise ValueError(f"selection_stage moet een van {', '.join(ESG_MANAGER_SELECTION_STAGES)} zijn")
    exc_end=(data.get("exception_end_date") or "").strip() or None
    if exc_end:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",exc_end): raise ValueError("exception_end_date moet ISO YYYY-MM-DD")
        date.fromisoformat(exc_end)
    if data.get("exception_rationale") and not data.get("exception_approver"):
        raise ValueError("exception_approver is verplicht bij een uitzondering")
    if data.get("exception_end_date") and not data.get("exception_rationale"):
        raise ValueError("exception_rationale is verplicht bij een uitzondering met einddatum")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["fund_ref"]),str(data["manager_ref"]))))
    pid=data.get("id") or f"esgms-{slug}-{stage}"
    actor=data.get("actor","demo.client-service").strip(); stamp=now(); cid=data["customer_id"]
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM esg_manager_selections WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO esg_manager_selections(id,version,customer_id,fund_ref,manager_ref,mandate_ref,
          selection_stage,min_esg_rating,exclusion_policy,inclusion_policy,esg_integration,
          climate_nature_human_rights,impact_targets_3d,thresholds,review_moment,next_review_at,
          exception_rationale,exception_approver,exception_end_date,source_ref,rationale,created_by,created_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,str(data["fund_ref"]).strip(),str(data["manager_ref"]).strip(),
           (data.get("mandate_ref") or "").strip() or None,stage,
           (data.get("min_esg_rating") or "").strip() or None,(data.get("exclusion_policy") or "").strip() or None,
           (data.get("inclusion_policy") or "").strip() or None,(data.get("esg_integration") or "").strip() or None,
           (data.get("climate_nature_human_rights") or "").strip() or None,
           (data.get("impact_targets_3d") or "").strip() or None,(data.get("thresholds") or "").strip() or None,
           (data.get("review_moment") or "").strip() or None,(data.get("next_review_at") or "").strip() or None,
           (data.get("exception_rationale") or "").strip() or None,(data.get("exception_approver") or "").strip() or None,
           exc_end,data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"esg_manager_selection",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"fund_ref":data["fund_ref"],"manager_ref":data["manager_ref"],
             "selection_stage":stage,"source_ref":data["source_ref"].strip()})
    with connect() as db: saved=db.execute("SELECT * FROM esg_manager_selections WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def esg_manager_selections(customer_id=None, fund_ref=None, manager_ref=None, valid_at=None):
    with connect() as db:
        q="SELECT * FROM esg_manager_selections WHERE 1=1"
        params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if fund_ref: q+=" AND fund_ref=?"; params.append(fund_ref)
        if manager_ref: q+=" AND manager_ref=?"; params.append(manager_ref)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    result=[dict(r) for r in rows]
    if valid_at:
        for r in result:
            r["validity_status"]="active" if (r.get("exception_end_date") is None or r["exception_end_date"]>=valid_at) else "expired"
    return result

def save_esg_contractual_flowdown(data):
    required=("customer_id","fund_ref","manager_ref","clause","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    target=data.get("target") or "direct_manager"
    if target not in ESG_FLOWDOWN_TARGETS: raise ValueError(f"target moet een van {', '.join(ESG_FLOWDOWN_TARGETS)} zijn")
    clause=data["clause"].strip()
    if clause not in ESG_FLOWDOWN_CLAUSES: raise ValueError(f"clause moet een van {', '.join(ESG_FLOWDOWN_CLAUSES)} zijn")
    exc_end=(data.get("exception_end_date") or "").strip() or None
    if exc_end:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",exc_end): raise ValueError("exception_end_date moet ISO YYYY-MM-DD")
        date.fromisoformat(exc_end)
    if data.get("exception_rationale") and not data.get("exception_approver"):
        raise ValueError("exception_approver is verplicht bij een uitzondering")
    if data.get("exception_end_date") and not data.get("exception_rationale"):
        raise ValueError("exception_rationale is verplicht bij een uitzondering met einddatum")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["fund_ref"]),str(data["manager_ref"]),clause)))
    pid=data.get("id") or f"esgfd-{slug}-{target}"
    actor=data.get("actor","demo.client-service").strip(); stamp=now(); cid=data["customer_id"]
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM esg_contractual_flowdowns WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO esg_contractual_flowdowns(id,version,customer_id,fund_ref,manager_ref,sub_manager_ref,
          target,clause,obligation_text,review_moment,next_review_at,
          exception_rationale,exception_approver,exception_end_date,source_ref,rationale,created_by,created_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,str(data["fund_ref"]).strip(),str(data["manager_ref"]).strip(),
           (data.get("sub_manager_ref") or "").strip() or None,target,clause,
           (data.get("obligation_text") or "").strip() or None,
           (data.get("review_moment") or "").strip() or None,(data.get("next_review_at") or "").strip() or None,
           (data.get("exception_rationale") or "").strip() or None,(data.get("exception_approver") or "").strip() or None,
           exc_end,data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"esg_contractual_flowdown",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"fund_ref":data["fund_ref"],"manager_ref":data["manager_ref"],
             "target":target,"clause":clause,"source_ref":data["source_ref"].strip()})
    with connect() as db: saved=db.execute("SELECT * FROM esg_contractual_flowdowns WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def esg_contractual_flowdowns(customer_id=None, fund_ref=None, manager_ref=None, clause=None, valid_at=None):
    with connect() as db:
        q="SELECT * FROM esg_contractual_flowdowns WHERE 1=1"
        params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if fund_ref: q+=" AND fund_ref=?"; params.append(fund_ref)
        if manager_ref: q+=" AND manager_ref=?"; params.append(manager_ref)
        if clause: q+=" AND clause=?"; params.append(clause)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    result=[dict(r) for r in rows]
    if valid_at:
        for r in result:
            r["validity_status"]="active" if (r.get("exception_end_date") is None or r["exception_end_date"]>=valid_at) else "expired"
    return result

def save_esg_due_diligence_dossier(data):
    required=("customer_id","fund_ref","manager_ref","workflow_step","finding","human_judgement","action_owner","deadline","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    step=data["workflow_step"].strip()
    if step not in ESG_DD_WORKFLOW_STEPS: raise ValueError(f"workflow_step moet een van {', '.join(ESG_DD_WORKFLOW_STEPS)} zijn")
    priority=(data.get("impact_priority") or "medium").strip()
    if priority not in ESG_DD_IMPACT_PRIORITIES: raise ValueError(f"impact_priority moet een van {', '.join(ESG_DD_IMPACT_PRIORITIES)} zijn")
    dl=data["deadline"].strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",dl): raise ValueError("deadline moet ISO YYYY-MM-DD")
    date.fromisoformat(dl)
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["fund_ref"]),str(data["manager_ref"]),step)))
    pid=data.get("id") or f"esgdd-{slug}"
    actor=data.get("actor","demo.client-service").strip(); stamp=now(); cid=data["customer_id"]
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM esg_due_diligence_dossiers WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO esg_due_diligence_dossiers(id,version,customer_id,fund_ref,manager_ref,workflow_step,impact_priority,finding,human_judgement,action_owner,deadline,source_ref,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,str(data["fund_ref"]).strip(),str(data["manager_ref"]).strip(),step,priority,
           data["finding"].strip(),data["human_judgement"].strip(),data["action_owner"].strip(),dl,
           data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"esg_due_diligence_dossier",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"fund_ref":data["fund_ref"],"manager_ref":data["manager_ref"],"workflow_step":step,"impact_priority":priority,"deadline":dl,"source_ref":data["source_ref"].strip()})
    with connect() as db: saved=db.execute("SELECT * FROM esg_due_diligence_dossiers WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def esg_due_diligence_dossiers(customer_id=None, fund_ref=None, manager_ref=None, workflow_step=None, valid_at=None):
    with connect() as db:
        q="SELECT * FROM esg_due_diligence_dossiers WHERE 1=1"
        params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if fund_ref: q+=" AND fund_ref=?"; params.append(fund_ref)
        if manager_ref: q+=" AND manager_ref=?"; params.append(manager_ref)
        if workflow_step: q+=" AND workflow_step=?"; params.append(workflow_step)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    result=[dict(r) for r in rows]
    if valid_at:
        for r in result:
            r["validity_status"]="active" if r["deadline"]>=valid_at else "overdue"
    return result

def save_esg_engagement_incident(data):
    required=("customer_id","fund_ref","manager_ref","incident","source_ref","severity","engagement_relation","engagement_goal","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    sev=data["severity"].strip()
    if sev not in ESG_ENGAGEMENT_SEVERITIES: raise ValueError(f"severity moet een van {', '.join(ESG_ENGAGEMENT_SEVERITIES)} zijn")
    progress=(data.get("progress") or "open").strip()
    if progress not in ESG_ENGAGEMENT_PROGRESS: raise ValueError(f"progress moet een van {', '.join(ESG_ENGAGEMENT_PROGRESS)} zijn")
    retention=(data.get("retention_decision") or "pending").strip()
    if retention not in ESG_ENGAGEMENT_RETENTION_DECISIONS: raise ValueError(f"retention_decision moet een van {', '.join(ESG_ENGAGEMENT_RETENTION_DECISIONS)} zijn")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["fund_ref"]),str(data["manager_ref"]),str(data["incident"]))))
    pid=data.get("id") or f"esgei-{slug}"
    actor=data.get("actor","demo.client-service").strip(); stamp=now(); cid=data["customer_id"]
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM esg_engagement_incidents WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO esg_engagement_incidents(id,version,customer_id,fund_ref,manager_ref,incident,source_ref,severity,engagement_relation,engagement_goal,progress,actions,remediation,closure,retention_decision,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,str(data["fund_ref"]).strip(),str(data["manager_ref"]).strip(),data["incident"].strip(),data["source_ref"].strip(),sev,data["engagement_relation"].strip(),data["engagement_goal"].strip(),progress,(data.get("actions") or "").strip() or None,(data.get("remediation") or "").strip() or None,(data.get("closure") or "").strip() or None,retention,data["rationale"].strip(),actor,stamp))
        audit(db,"esg_engagement_incident",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"fund_ref":data["fund_ref"],"manager_ref":data["manager_ref"],"severity":sev,"progress":progress,"retention_decision":retention,"source_ref":data["source_ref"].strip()})
    with connect() as db: saved=db.execute("SELECT * FROM esg_engagement_incidents WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def esg_engagement_incidents(customer_id=None, fund_ref=None, manager_ref=None, severity=None, progress=None, valid_at=None):
    with connect() as db:
        q="SELECT * FROM esg_engagement_incidents WHERE 1=1"
        params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if fund_ref: q+=" AND fund_ref=?"; params.append(fund_ref)
        if manager_ref: q+=" AND manager_ref=?"; params.append(manager_ref)
        if severity: q+=" AND severity=?"; params.append(severity)
        if progress: q+=" AND progress=?"; params.append(progress)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    result=[dict(r) for r in rows]
    if valid_at:
        for r in result:
            r["validity_status"]="active" if r["progress"]!="closed" else "closed"
    return result

def save_esg_periodic_review(data):
    required=("customer_id","fund_ref","manager_ref","esg_risks","results","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    period=(data.get("review_period") or "annual").strip()
    if period not in ESG_REVIEW_PERIODS: raise ValueError(f"review_period moet een van {', '.join(ESG_REVIEW_PERIODS)} zijn")
    deviation=(data.get("deviation") or "none").strip()
    if deviation not in ESG_REVIEW_DEVIATIONS: raise ValueError(f"deviation moet een van {', '.join(ESG_REVIEW_DEVIATIONS)} zijn")
    escalation=(data.get("escalation") or "none").strip()
    if escalation not in ESG_REVIEW_ESCALATIONS: raise ValueError(f"escalation moet een van {', '.join(ESG_REVIEW_ESCALATIONS)} zijn")
    if deviation in ("deviation","deferral") and (not data.get("deviation_rationale") or not str(data["deviation_rationale"]).strip()):
        raise ValueError("deviation_rationale is verplicht bij afwijking/uitstel")
    if deviation in ("deviation","deferral") and (not data.get("approver") or not str(data["approver"]).strip()):
        raise ValueError("approver is verplicht bij afwijking/uitstel")
    if deviation in ("deviation","deferral") and (not data.get("end_date") or not str(data["end_date"]).strip()):
        raise ValueError("end_date is verplicht bij afwijking/uitstel")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["fund_ref"]),str(data["manager_ref"]),str(data.get("review_period","annual")))))
    pid=data.get("id") or f"esgpr-{slug}"
    actor=data.get("actor","demo.client-service").strip(); stamp=now(); cid=data["customer_id"]
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM esg_periodic_reviews WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO esg_periodic_reviews(id,version,customer_id,fund_ref,manager_ref,review_period,esg_risks,results,improvement_actions,deviation,deviation_rationale,approver,end_date,escalation,source_ref,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,str(data["fund_ref"]).strip(),str(data["manager_ref"]).strip(),period,data["esg_risks"].strip(),data["results"].strip(),(data.get("improvement_actions") or "").strip() or None,deviation,(data.get("deviation_rationale") or "").strip() or None,(data.get("approver") or "").strip() or None,(data.get("end_date") or "").strip() or None,escalation,data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"esg_periodic_review",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"fund_ref":data["fund_ref"],"manager_ref":data["manager_ref"],"review_period":period,"deviation":deviation,"escalation":escalation,"source_ref":data["source_ref"].strip()})
    with connect() as db: saved=db.execute("SELECT * FROM esg_periodic_reviews WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def esg_periodic_reviews(customer_id=None, fund_ref=None, manager_ref=None, review_period=None, deviation=None, escalation=None, valid_at=None):
    with connect() as db:
        q="SELECT * FROM esg_periodic_reviews WHERE 1=1"
        params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if fund_ref: q+=" AND fund_ref=?"; params.append(fund_ref)
        if manager_ref: q+=" AND manager_ref=?"; params.append(manager_ref)
        if review_period: q+=" AND review_period=?"; params.append(review_period)
        if deviation: q+=" AND deviation=?"; params.append(deviation)
        if escalation: q+=" AND escalation=?"; params.append(escalation)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    result=[dict(r) for r in rows]
    if valid_at:
        for r in result:
            r["validity_status"]="active" if r["deviation"]!="deferral" else "deferred"
    return result

def save_reporting_catalog_item(data):
    required=("customer_id","report_type","data_item","definition","unit","perimeter","calculation_source","frequency","recipients","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["report_type"] not in REPORTING_TYPES: raise ValueError(f"report_type moet een van {', '.join(REPORTING_TYPES)} zijn")
    if data["frequency"] not in REPORTING_FREQUENCIES: raise ValueError(f"frequency moet een van {', '.join(REPORTING_FREQUENCIES)} zijn")
    language=(data.get("language") or "nl").strip()
    if language not in REPORTING_LANGUAGES: raise ValueError(f"language moet een van {', '.join(REPORTING_LANGUAGES)} zijn")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["report_type"]),str(data["data_item"]))))
    pid=data.get("id") or f"rpt-{slug}"
    actor=data.get("actor","demo.client-service").strip(); stamp=now(); cid=data["customer_id"]
    recipients=data["recipients"]
    if isinstance(recipients,(list,tuple)): recipients=json.dumps(recipients)
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM reporting_catalog WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO reporting_catalog(id,version,customer_id,report_type,data_item,definition,unit,perimeter,scope,calculation_source,frequency,deadline,language,template_ref,recipients,schema_version,methodology_version,source_ref,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,str(data["report_type"]).strip(),data["data_item"].strip(),data["definition"].strip(),data["unit"].strip(),data["perimeter"].strip(),(data.get("scope") or "").strip() or None,data["calculation_source"].strip(),data["frequency"].strip(),(data.get("deadline") or "").strip() or None,language,(data.get("template_ref") or "").strip() or None,recipients,(data.get("schema_version") or "").strip() or None,(data.get("methodology_version") or "").strip() or None,data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"reporting_catalog",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"report_type":data["report_type"],"data_item":data["data_item"],"frequency":data["frequency"]})
    with connect() as db: saved=db.execute("SELECT * FROM reporting_catalog WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def reporting_catalog_items(customer_id=None, report_type=None, frequency=None):
    with connect() as db:
        q="SELECT * FROM reporting_catalog WHERE 1=1"
        params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if report_type: q+=" AND report_type=?"; params.append(report_type)
        if frequency: q+=" AND frequency=?"; params.append(frequency)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]
def data_delivery_agreements(customer_id=None, supplier_role=None, field=None):
    with connect() as db:
        q="SELECT * FROM data_delivery_agreements WHERE 1=1"
        params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if supplier_role: q+=" AND supplier_role=?"; params.append(supplier_role)
        if field: q+=" AND field=?"; params.append(field)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def save_data_delivery_agreement(data):
    required=("customer_id","supplier_ref","supplier_role","field","period","channel","validation","proof","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["supplier_role"] not in SUPPLIER_ROLES: raise ValueError(f"supplier_role moet een van {', '.join(SUPPLIER_ROLES)} zijn")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["supplier_role"]),str(data["field"]),str(data["period"]))))
    pid=data.get("id") or f"dda-{slug}"
    actor=data.get("actor","demo.client-service").strip(); stamp=now(); cid=data["customer_id"]
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM data_delivery_agreements WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO data_delivery_agreements(id,version,customer_id,supplier_ref,supplier_role,field,period,channel,validation,proof,source_ref,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,data["supplier_ref"].strip(),data["supplier_role"].strip(),data["field"].strip(),data["period"].strip(),data["channel"].strip(),data["validation"].strip(),data["proof"].strip(),data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"data_delivery_agreements",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"supplier_role":data["supplier_role"],"field":data["field"],"period":data["period"]})
    with connect() as db: saved=db.execute("SELECT * FROM data_delivery_agreements WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def sfdr_pai_profiles(customer_id=None, profile_name=None, responsibility=None):
    with connect() as db:
        q="SELECT * FROM sfdr_pai_profiles WHERE 1=1"
        params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if profile_name: q+=" AND profile_name=?"; params.append(profile_name)
        if responsibility: q+=" AND responsibility=?"; params.append(responsibility)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def save_sfdr_pai_profile(data):
    required=("customer_id","profile_name","pai_indicators","reference_period","reporting_frequency","methodology","data_coverage","missing_data_reason","assurance","responsibility","applicability_decision_ref","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["reporting_frequency"] not in REPORTING_FREQUENCIES: raise ValueError(f"reporting_frequency moet een van {', '.join(REPORTING_FREQUENCIES)} zijn")
    indicators=data["pai_indicators"]
    if isinstance(indicators,(list,tuple)): indicators=json.dumps(indicators)
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["profile_name"]))))
    pid=data.get("id") or f"sfdr-pai-{slug}"
    actor=data.get("actor","demo.client-service").strip(); stamp=now(); cid=data["customer_id"]
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM sfdr_pai_profiles WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO sfdr_pai_profiles(id,version,customer_id,profile_name,pai_indicators,reference_period,reporting_frequency,methodology,data_coverage,missing_data_reason,assurance,responsibility,applicability_decision_ref,schema_version,methodology_version,source_ref,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,data["profile_name"].strip(),indicators,data["reference_period"].strip(),data["reporting_frequency"].strip(),data["methodology"].strip(),data["data_coverage"].strip(),data["missing_data_reason"].strip(),data["assurance"].strip(),data["responsibility"].strip(),data["applicability_decision_ref"].strip(),(data.get("schema_version") or "").strip() or None,(data.get("methodology_version") or "").strip() or None,data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"sfdr_pai_profiles",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"profile_name":data["profile_name"],"reporting_frequency":data["reporting_frequency"]})
    with connect() as db: saved=db.execute("SELECT * FROM sfdr_pai_profiles WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

COMPLY_OR_EXPLAIN_STATUSES=("comply","explain","deviation")

def comply_or_explain(customer_id=None, code_ref=None, compliance_status=None):
    with connect() as db:
        q="SELECT * FROM comply_or_explain WHERE 1=1"
        params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if code_ref: q+=" AND code_ref=?"; params.append(code_ref)
        if compliance_status: q+=" AND compliance_status=?"; params.append(compliance_status)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def save_comply_or_explain(data):
    required=("customer_id","code_ref","compliance_status","deviation_explanation","validity_from","validity_to","impact","approver","follow_up_action","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["compliance_status"] not in COMPLY_OR_EXPLAIN_STATUSES: raise ValueError(f"compliance_status moet een van {', '.join(COMPLY_OR_EXPLAIN_STATUSES)} zijn")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["code_ref"]))))
    cid=data["customer_id"]; ceid=data.get("id") or f"comply-explain-{slug}"
    actor=data.get("actor","demo.client-service").strip(); stamp=now()
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM comply_or_explain WHERE id=? AND customer_id=?",(ceid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO comply_or_explain(id,version,customer_id,code_ref,compliance_status,deviation_explanation,validity_from,validity_to,impact,approver,follow_up_action,source_ref,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (ceid,version,cid,data["code_ref"].strip(),data["compliance_status"].strip(),data["deviation_explanation"].strip(),data["validity_from"].strip(),data["validity_to"].strip(),data["impact"].strip(),data["approver"].strip(),data["follow_up_action"].strip(),data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"comply_or_explain",ceid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"code_ref":data["code_ref"],"compliance_status":data["compliance_status"]})
    with connect() as db: saved=db.execute("SELECT * FROM comply_or_explain WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(ceid,cid)).fetchone()
    return dict(saved)

def reporting_executions(customer_id=None, report_ref=None, delivery_status=None):
    with connect() as db:
        q="SELECT * FROM reporting_executions WHERE 1=1"
        params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if report_ref: q+=" AND report_ref=?"; params.append(report_ref)
        if delivery_status: q+=" AND delivery_status=?"; params.append(delivery_status)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def save_reporting_execution(data):
    required=("customer_id","report_ref","calendar_period","deadline","delivery_status","completeness","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["delivery_status"] not in REPORTING_EXECUTION_STATUSES: raise ValueError(f"delivery_status moet een van {', '.join(REPORTING_EXECUTION_STATUSES)} zijn")
    escalation=(data.get("escalation") or "none").strip()
    if escalation not in REPORTING_ESCALATION_LEVELS: raise ValueError(f"escalation moet een van {', '.join(REPORTING_ESCALATION_LEVELS)} zijn")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["report_ref"]),str(data["calendar_period"]))))
    eid=data.get("id") or f"rpt-exec-{slug}"
    actor=data.get("actor","demo.client-service").strip(); stamp=now(); cid=data["customer_id"]
    delay=int(data.get("delay_days") or 0)
    errors=data.get("data_quality_errors")
    if isinstance(errors,(list,tuple)): errors=json.dumps(errors)
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM reporting_executions WHERE id=? AND customer_id=?",(eid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO reporting_executions(id,version,customer_id,report_ref,calendar_period,deadline,delivery_status,completeness,data_quality_errors,delay_days,incident_ref,recovery_action,escalation,approved_report_ref,schema_version,methodology_version,source_ref,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (eid,version,cid,data["report_ref"].strip(),data["calendar_period"].strip(),data["deadline"].strip(),data["delivery_status"].strip(),data["completeness"].strip(),errors,delay,(data.get("incident_ref") or "").strip() or None,(data.get("recovery_action") or "").strip() or None,escalation,(data.get("approved_report_ref") or "").strip() or None,(data.get("schema_version") or "").strip() or None,(data.get("methodology_version") or "").strip() or None,data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"reporting_executions",eid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"report_ref":data["report_ref"],"delivery_status":data["delivery_status"]})
    with connect() as db: saved=db.execute("SELECT * FROM reporting_executions WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(eid,cid)).fetchone()
    return dict(saved)

def transparency_outputs(customer_id=None, disclosure_ref=None, publication_consent=None):
    with connect() as db:
        q="SELECT * FROM transparency_outputs WHERE 1=1"
        params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if disclosure_ref: q+=" AND disclosure_ref=?"; params.append(disclosure_ref)
        if publication_consent: q+=" AND publication_consent=?"; params.append(publication_consent)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def save_transparency_output(data):
    required=("customer_id","disclosure_ref","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    confidentiality=(data.get("confidentiality_flag") or "confidential").strip()
    if confidentiality not in TRANSPARENCY_CONFIDENTIALITY_FLAGS: raise ValueError(f"confidentiality_flag moet een van {', '.join(TRANSPARENCY_CONFIDENTIALITY_FLAGS)} zijn")
    consent=(data.get("publication_consent") or "pending").strip()
    if consent not in TRANSPARENCY_PUBLICATION_CONSENTS: raise ValueError(f"publication_consent moet een van {', '.join(TRANSPARENCY_PUBLICATION_CONSENTS)} zijn")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["disclosure_ref"]))))
    toid=data.get("id") or f"transp-{slug}"
    actor=data.get("actor","demo.client-service").strip(); stamp=now(); cid=data["customer_id"]
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM transparency_outputs WHERE id=? AND customer_id=?",(toid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO transparency_outputs(id,version,customer_id,disclosure_ref,manager_ref,data_coverage,confidentiality_flag,publication_consent,publication_scope,schema_version,methodology_version,source_ref,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (toid,version,cid,data["disclosure_ref"].strip(),(data.get("manager_ref") or "").strip() or None,(data.get("data_coverage") or "").strip() or None,confidentiality,consent,(data.get("publication_scope") or "").strip() or None,(data.get("schema_version") or "").strip() or None,(data.get("methodology_version") or "").strip() or None,data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"transparency_outputs",toid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"disclosure_ref":data["disclosure_ref"],"publication_consent":consent})
    with connect() as db: saved=db.execute("SELECT * FROM transparency_outputs WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(toid,cid)).fetchone()
    return dict(saved)

# WTP-001 transitieprofiel: geldige waarden voor de transitiefase.
WTP_DATA_PHASES=("voor","tijdens","na","beheer")
WTP_TRANSITION_PHASES=("preparation","decision","migration","golive","aftercare","closed")

def wtp_transition_profiles(customer_id=None, fund_ref=None, transition_phase=None, owner=None):
    with connect() as db:
        q="SELECT * FROM wtp_transition_profiles WHERE 1=1"
        params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if fund_ref: q+=" AND fund_ref=?"; params.append(fund_ref)
        if transition_phase: q+=" AND transition_phase=?"; params.append(transition_phase)
        if owner: q+=" AND owner=?"; params.append(owner)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def save_wtp_transition_profile(data):
    required=("customer_id","fund_ref","fund_regulation","transition_phase","planning","scope","owner","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["transition_phase"] not in WTP_TRANSITION_PHASES: raise ValueError(f"transition_phase moet een van {', '.join(WTP_TRANSITION_PHASES)} zijn")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["fund_ref"]))))
    pid=data.get("id") or f"wtp-{slug}"
    actor=data.get("actor","demo.client-service").strip(); stamp=now(); cid=data["customer_id"]
    decision_date=(data.get("decision_date") or "").strip() or None
    golive_date=(data.get("golive_date") or "").strip() or None
    migration_date=(data.get("migration_date") or "").strip() or None
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM wtp_transition_profiles WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO wtp_transition_profiles(id,version,customer_id,fund_ref,fund_regulation,transition_phase,planning,scope,decision_date,golive_date,migration_date,owner,source_ref,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,data["fund_ref"].strip(),data["fund_regulation"].strip(),data["transition_phase"].strip(),data["planning"].strip(),data["scope"].strip(),decision_date,golive_date,migration_date,data["owner"].strip(),data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"wtp_transition_profiles",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"fund_ref":data["fund_ref"],"transition_phase":data["transition_phase"]})
    with connect() as db: saved=db.execute("SELECT * FROM wtp_transition_profiles WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()

    return dict(saved)

# WTP-002 RACI en afhankelijkheden: geldige partijrollen.
WTP_RACI_PARTY_ROLES=("fonds","PUO","fiduciair","manager","custodian","technologiepartij")

def wtp_raci_dependencies(customer_id=None, fund_ref=None, party_role=None, party_name=None):
    with connect() as db:
        q="SELECT * FROM wtp_raci_dependencies WHERE 1=1"
        params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if fund_ref: q+=" AND fund_ref=?"; params.append(fund_ref)
        if party_role: q+=" AND party_role=?"; params.append(party_role)
        if party_name: q+=" AND party_name=?"; params.append(party_name)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def save_wtp_raci_dependency(data):
    required=("customer_id","fund_ref","party_role","party_name","task","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["party_role"] not in WTP_RACI_PARTY_ROLES: raise ValueError(f"party_role moet een van {', '.join(WTP_RACI_PARTY_ROLES)} zijn")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["fund_ref"]),str(data["party_role"]))))
    pid=data.get("id") or f"wtp-raci-{slug}"
    actor=data.get("actor","demo.client-service").strip() if str(data.get("actor","demo.client-service")).strip() else "demo.client-service"
    stamp=now(); cid=data["customer_id"]
    def opt(k): 
        v=data.get(k)
        return (str(v).strip() if v is not None else None) or None
    input_v=opt("input"); output_v=opt("output"); handoff_v=opt("handoff"); dependency_v=opt("dependency")
    escalation_v=opt("escalation"); milestone_v=opt("critical_milestone"); evidence_v=opt("evidence_status")
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM wtp_raci_dependencies WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO wtp_raci_dependencies(id,version,customer_id,fund_ref,party_role,party_name,task,input,output,handoff,dependency,escalation,critical_milestone,evidence_status,source_ref,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,data["fund_ref"].strip(),data["party_role"].strip(),data["party_name"].strip(),data["task"].strip(),input_v,output_v,handoff_v,dependency_v,escalation_v,milestone_v,evidence_v,data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"wtp_raci_dependencies",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"fund_ref":data["fund_ref"],"party_role":data["party_role"]})
    with connect() as db: saved=db.execute("SELECT * FROM wtp_raci_dependencies WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def wtp_transition_data(customer_id=None, fund_ref=None, data_phase=None, data_item=None):
    with connect() as db:
        q="SELECT * FROM wtp_transition_data WHERE 1=1"
        params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if fund_ref: q+=" AND fund_ref=?"; params.append(fund_ref)
        if data_phase: q+=" AND data_phase=?"; params.append(data_phase)
        if data_item: q+=" AND data_item=?"; params.append(data_item)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def save_wtp_transition_data(data):
    required=("customer_id","fund_ref","data_item","data_phase","owner","source","frequency","validation_rule","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["data_phase"] not in WTP_DATA_PHASES: raise ValueError(f"data_phase moet een van {', '.join(WTP_DATA_PHASES)} zijn")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["fund_ref"]),str(data["data_item"]),str(data["data_phase"]))))
    pid=data.get("id") or f"wtp-data-{slug}"
    actor=data.get("actor","demo.client-service").strip() if str(data.get("actor","demo.client-service")).strip() else "demo.client-service"
    stamp=now(); cid=data["customer_id"]
    def opt(k):
        v=data.get(k)
        return (str(v).strip() if v is not None else None) or None
    reconciliation_v=opt("reconciliation"); norm_v=opt("data_quality_norm"); evidence_v=opt("evidence"); continuity_v=opt("continuity_agreement")
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM wtp_transition_data WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO wtp_transition_data(id,version,customer_id,fund_ref,data_item,data_phase,owner,source,frequency,validation_rule,reconciliation,data_quality_norm,evidence,continuity_agreement,source_ref,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,data["fund_ref"].strip(),data["data_item"].strip(),data["data_phase"].strip(),data["owner"].strip(),data["source"].strip(),data["frequency"].strip(),data["validation_rule"].strip(),reconciliation_v,norm_v,evidence_v,continuity_v,data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"wtp_transition_data",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"fund_ref":data["fund_ref"],"data_phase":data["data_phase"]})
    with connect() as db: saved=db.execute("SELECT * FROM wtp_transition_data WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

# WTP-004 Mijlpalen en gereedheidscriteria: geldige bewijsstatussen.
WTP_MILESTONE_EVIDENCE_STATUSES=("open","in_progress","validated","go","no_go")

def wtp_milestones(customer_id=None, fund_ref=None, deliverable=None, evidence_status=None):
    with connect() as db:
        q="SELECT * FROM wtp_milestones WHERE 1=1"
        params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if fund_ref: q+=" AND fund_ref=?"; params.append(fund_ref)
        if deliverable: q+=" AND deliverable=?"; params.append(deliverable)
        if evidence_status: q+=" AND evidence_status=?"; params.append(evidence_status)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def save_wtp_milestone(data):
    required=("customer_id","fund_ref","deliverable","validation_criteria","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data.get("evidence_status") not in (None,"") and data["evidence_status"] not in WTP_MILESTONE_EVIDENCE_STATUSES:
        raise ValueError(f"evidence_status moet een van {', '.join(WTP_MILESTONE_EVIDENCE_STATUSES)} zijn")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["fund_ref"]),str(data["deliverable"]))))
    pid=data.get("id") or f"wtp-ms-{slug}"
    actor=data.get("actor","demo.client-service").strip() if str(data.get("actor","demo.client-service")).strip() else "demo.client-service"
    stamp=now(); cid=data["customer_id"]
    def opt(k):
        v=data.get(k)
        return (str(v).strip() if v is not None else None) or None
    planning_v=opt("planning"); progress_v=opt("progress_report"); risk_v=opt("risk_impact")
    recovery_v=opt("recovery_plan"); gonogo_v=opt("go_no_go_evidence"); status_v=opt("evidence_status")
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM wtp_milestones WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO wtp_milestones(id,version,customer_id,fund_ref,deliverable,planning,validation_criteria,progress_report,risk_impact,recovery_plan,go_no_go_evidence,evidence_status,source_ref,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,data["fund_ref"].strip(),data["deliverable"].strip(),planning_v,data["validation_criteria"].strip(),progress_v,risk_v,recovery_v,gonogo_v,status_v,data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"wtp_milestones",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"fund_ref":data["fund_ref"],"deliverable":data["deliverable"]})
    with connect() as db: saved=db.execute("SELECT * FROM wtp_milestones WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

# WTP-005 Risico's en wijzigingsbeheer: geldige risicocategorieen en bewijsstatussen.
WTP_RISK_CATEGORIES=("operational","data","IT","financial","chain")
WTP_RISK_EVIDENCE_STATUSES=("open","mitigated","accepted","closed")

def wtp_risks(customer_id=None, fund_ref=None, risk_category=None, evidence_status=None):
    with connect() as db:
        q="SELECT * FROM wtp_risks WHERE 1=1"
        params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if fund_ref: q+=" AND fund_ref=?"; params.append(fund_ref)
        if risk_category: q+=" AND risk_category=?"; params.append(risk_category)
        if evidence_status: q+=" AND evidence_status=?"; params.append(evidence_status)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def save_wtp_risk(data):
    required=("customer_id","fund_ref","risk_category","risk_description","mitigation","change_impact","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["risk_category"] not in WTP_RISK_CATEGORIES:
        raise ValueError(f"risk_category moet een van {', '.join(WTP_RISK_CATEGORIES)} zijn")
    if data.get("evidence_status") not in (None,"") and data["evidence_status"] not in WTP_RISK_EVIDENCE_STATUSES:
        raise ValueError(f"evidence_status moet een van {', '.join(WTP_RISK_EVIDENCE_STATUSES)} zijn")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["fund_ref"]),str(data["risk_category"]))))
    pid=data.get("id") or f"wtp-risk-{slug}"
    actor=data.get("actor","demo.client-service").strip() if str(data.get("actor","demo.client-service")).strip() else "demo.client-service"
    stamp=now(); cid=data["customer_id"]
    def opt(k):
        v=data.get(k); return (str(v).strip() if v is not None else None) or None
    affected_v=opt("affected_roles"); required_data_v=opt("required_data"); missing_v=opt("missing_interfaces")
    milestone_v=opt("critical_milestone"); status_v=opt("evidence_status")
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM wtp_risks WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO wtp_risks(id,version,customer_id,fund_ref,risk_category,risk_description,mitigation,change_impact,affected_roles,required_data,missing_interfaces,critical_milestone,evidence_status,source_ref,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,data["fund_ref"].strip(),data["risk_category"].strip(),data["risk_description"].strip(),data["mitigation"].strip(),data["change_impact"].strip(),affected_v,required_data_v,missing_v,milestone_v,status_v,data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"wtp_risks",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"fund_ref":data["fund_ref"],"risk_category":data["risk_category"]})
    with connect() as db: saved=db.execute("SELECT * FROM wtp_risks WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

FEE_COMPONENT_TYPES=("aum","fixed","performance","minimum","discount","side_letter","indexation")
FEE_FREQUENCIES=("monthly","quarterly","semiannual","annual","on_demand")
FEE_CURRENCIES=("EUR","USD","GBP","CHF")

def fee_components(customer_id=None, fund_ref=None, fee_type=None, currency=None):
    with connect() as db:
        q="SELECT * FROM fee_components WHERE 1=1"
        params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if fund_ref: q+=" AND fund_ref=?"; params.append(fund_ref)
        if fee_type: q+=" AND fee_type=?"; params.append(fee_type)
        if currency: q+=" AND currency=?"; params.append(currency)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def save_fee_component(data):
    required=("customer_id","fund_ref","fee_type","fee_name","currency","accrual_frequency","invoice_frequency","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["fee_type"] not in FEE_COMPONENT_TYPES:
        raise ValueError(f"fee_type moet een van {', '.join(FEE_COMPONENT_TYPES)} zijn")
    if data["currency"] not in FEE_CURRENCIES:
        raise ValueError(f"currency moet een van {', '.join(FEE_CURRENCIES)} zijn")
    if data["accrual_frequency"] not in FEE_FREQUENCIES:
        raise ValueError(f"accrual_frequency moet een van {', '.join(FEE_FREQUENCIES)} zijn")
    if data["invoice_frequency"] not in FEE_FREQUENCIES:
        raise ValueError(f"invoice_frequency moet een van {', '.join(FEE_FREQUENCIES)} zijn")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["fund_ref"]),str(data["fee_type"]),str(data["fee_name"]))))
    pid=data.get("id") or f"fee-{slug}"
    actor=data.get("actor","demo.client-service").strip() if str(data.get("actor","demo.client-service")).strip() else "demo.client-service"
    stamp=now(); cid=data["customer_id"]
    def opt(k):
        v=data.get(k); return (str(v).strip() if v is not None else None) or None
    def optf(k):
        v=data.get(k)
        if v is None or v=="": return None
        return float(v)
    hwm=data.get("high_water_mark")
    hwm_v=1 if hwm in (True,1,"1","true","True","yes") else (0 if hwm in (False,0,"0","false","False","no") else None)
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM fee_components WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO fee_components(id,version,customer_id,fund_ref,fee_type,fee_name,rate_bps,tier_from,tier_to,minimum_amount,minimum_currency,fixed_amount,fixed_currency,fixed_frequency,performance_fee_pct,hurdle_rate_pct,high_water_mark,discount_pct,side_letter_ref,currency,accrual_frequency,invoice_frequency,indexation_basis,indexation_frequency,effective_from,effective_to,source_ref,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,data["fund_ref"].strip(),data["fee_type"].strip(),data["fee_name"].strip(),
           optf("rate_bps"),optf("tier_from"),optf("tier_to"),optf("minimum_amount"),opt("minimum_currency"),
           optf("fixed_amount"),opt("fixed_currency"),opt("fixed_frequency"),optf("performance_fee_pct"),
           optf("hurdle_rate_pct"),hwm_v,optf("discount_pct"),opt("side_letter_ref"),data["currency"].strip(),
           data["accrual_frequency"].strip(),data["invoice_frequency"].strip(),opt("indexation_basis"),
           opt("indexation_frequency"),opt("effective_from"),opt("effective_to"),data["source_ref"].strip(),
           data["rationale"].strip(),actor,stamp))
        audit(db,"fee_components",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"fund_ref":data["fund_ref"],"fee_type":data["fee_type"]})
    with connect() as db: saved=db.execute("SELECT * FROM fee_components WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

FEE_CALCULATION_BASES=("aum","committed_capital","invested_capital","nav")
FEE_MEASUREMENT_PERIODS=("daily","monthly","quarterly","semiannual","annual")
FEE_VALUATION_INPUTS=("eod_nav","average_aum","closing_aum","committed")
FEE_ROUNDING_MODES=("half_up","half_even","floor","ceil")

def save_fee_calculation_rule(data):
    required=("customer_id","fund_ref","rule_name","base","measurement_period","valuation_input","rounding_mode","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["base"] not in FEE_CALCULATION_BASES: raise ValueError(f"base moet een van {', '.join(FEE_CALCULATION_BASES)} zijn")
    if data["measurement_period"] not in FEE_MEASUREMENT_PERIODS: raise ValueError(f"measurement_period moet een van {', '.join(FEE_MEASUREMENT_PERIODS)} zijn")
    if data["valuation_input"] not in FEE_VALUATION_INPUTS: raise ValueError(f"valuation_input moet een van {', '.join(FEE_VALUATION_INPUTS)} zijn")
    if data["rounding_mode"] not in FEE_ROUNDING_MODES: raise ValueError(f"rounding_mode moet een van {', '.join(FEE_ROUNDING_MODES)} zijn")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["fund_ref"]),str(data["rule_name"]))))
    pid=data.get("id") or f"feerule-{slug}"
    actor=data.get("actor","demo.client-service").strip() if str(data.get("actor","demo.client-service")).strip() else "demo.client-service"
    stamp=now(); cid=data["customer_id"]
    def opt(k):
        v=data.get(k); return (str(v).strip() if v is not None else None) or None
    def optf(k):
        v=data.get(k)
        if v is None or v=="": return None
        return float(v)
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM fee_calculation_rules WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO fee_calculation_rules(id,version,customer_id,fund_ref,rule_name,base,measurement_period,valuation_input,fx_basis,rounding_mode,cap_amount,floor_amount,edge_case,effective_from,effective_to,source_ref,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,data["fund_ref"].strip(),data["rule_name"].strip(),data["base"].strip(),data["measurement_period"].strip(),data["valuation_input"].strip(),opt("fx_basis"),data["rounding_mode"].strip(),optf("cap_amount"),optf("floor_amount"),opt("edge_case"),opt("effective_from"),opt("effective_to"),data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"fee_calculation_rules",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),{"customer_id":cid,"version":version})
    with connect() as db: saved=db.execute("SELECT * FROM fee_calculation_rules WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def fee_calculation_rules(customer_id=None, fund_ref=None, base=None):
    with connect() as db:
        q="SELECT * FROM fee_calculation_rules WHERE 1=1"; params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if fund_ref: q+=" AND fund_ref=?"; params.append(fund_ref)
        if base: q+=" AND base=?"; params.append(base)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def fee_calculation_rules_export(customer_id=None, fund_ref=None):
    rows=fee_calculation_rules(customer_id=customer_id,fund_ref=fund_ref)
    return {"generated_at":now(),"perimeter":{"customer_id":customer_id,"fund_ref":fund_ref},"coverage":len(rows),"rows":rows}

COST_OVERVIEW_TYPES=("direct_fee","performance_fee","other_agreed")
DISCLOSURE_PERMISSIONS=("permitted","restricted","prohibited")
PERIMETERS=("client","mandate","product")

def save_cost_overview(data):
    required=("customer_id","fund_ref","cost_type","source_ref","recipient","period_start","period_end","perimeter","amount","currency","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["cost_type"] not in COST_OVERVIEW_TYPES: raise ValueError(f"cost_type moet een van {', '.join(COST_OVERVIEW_TYPES)} zijn")
    if data["currency"] not in FEE_CURRENCIES: raise ValueError(f"currency moet een van {', '.join(FEE_CURRENCIES)} zijn")
    if data["perimeter"] not in PERIMETERS: raise ValueError(f"perimeter moet een van {', '.join(PERIMETERS)} zijn")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["fund_ref"]),str(data["cost_type"]),str(data["recipient"]),str(data["period_start"]),str(data["period_end"]))))
    pid=data.get("id") or f"cost-{slug}"
    actor=data.get("actor","demo.client-service").strip() if str(data.get("actor","demo.client-service")).strip() else "demo.client-service"
    stamp=now(); cid=data["customer_id"]
    def opt(k):
        v=data.get(k); return (str(v).strip() if v is not None else None) or None
    def optf(k):
        v=data.get(k)
        if v is None or v=="": return None
        return float(v)
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM cost_overview WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO cost_overview(id,version,customer_id,fund_ref,mandate_ref,product_ref,cost_type,source_ref,recipient,period_start,period_end,perimeter,amount,currency,allocation_basis,coverage_pct,effective_from,effective_to,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,data["fund_ref"].strip(),opt("mandate_ref"),opt("product_ref"),data["cost_type"].strip(),data["source_ref"].strip(),data["recipient"].strip(),data["period_start"].strip(),data["period_end"].strip(),data["perimeter"].strip(),float(data["amount"]),data["currency"].strip(),opt("allocation_basis"),optf("coverage_pct"),opt("effective_from"),opt("effective_to"),data["rationale"].strip(),actor,stamp))
        audit(db,"cost_overview",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),{"customer_id":cid,"version":version,"cost_type":data["cost_type"]})
    with connect() as db: saved=db.execute("SELECT * FROM cost_overview WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def cost_overview(customer_id=None, fund_ref=None, cost_type=None, perimeter=None):
    with connect() as db:
        q="SELECT * FROM cost_overview WHERE 1=1"; params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if fund_ref: q+=" AND fund_ref=?"; params.append(fund_ref)
        if cost_type: q+=" AND cost_type=?"; params.append(cost_type)
        if perimeter: q+=" AND perimeter=?"; params.append(perimeter)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def cost_overview_export(customer_id=None, fund_ref=None, perimeter=None):
    rows=cost_overview(customer_id=customer_id,fund_ref=fund_ref,perimeter=perimeter)
    return {"generated_at":now(),"perimeter":{"customer_id":customer_id,"fund_ref":fund_ref,"perimeter":perimeter},"coverage":len(rows),"rows":rows}

def save_manager_look_through(data):
    required=("customer_id","manager_ref","fund_ref","asset_class","coverage_date","disclosure_permission","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["disclosure_permission"] not in DISCLOSURE_PERMISSIONS: raise ValueError(f"disclosure_permission moet een van {', '.join(DISCLOSURE_PERMISSIONS)} zijn")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["manager_ref"]),str(data["fund_ref"]),str(data["asset_class"]),str(data["coverage_date"]))))
    pid=data.get("id") or f"mgrlt-{slug}"
    actor=data.get("actor","demo.client-service").strip() if str(data.get("actor","demo.client-service")).strip() else "demo.client-service"
    stamp=now(); cid=data["customer_id"]
    def opt(k):
        v=data.get(k); return (str(v).strip() if v is not None else None) or None
    def optf(k):
        v=data.get(k)
        if v is None or v=="": return None
        return float(v)
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM manager_look_through WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO manager_look_through(id,version,customer_id,manager_ref,fund_ref,vehicle_ref,mandate_ref,asset_class,aum,coverage_date,disclosure_permission,data_coverage,source_ref,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,data["manager_ref"].strip(),data["fund_ref"].strip(),opt("vehicle_ref"),opt("mandate_ref"),data["asset_class"].strip(),optf("aum"),data["coverage_date"].strip(),data["disclosure_permission"].strip(),opt("data_coverage"),data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"manager_look_through",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),{"customer_id":cid,"version":version,"manager_ref":data["manager_ref"],"disclosure_permission":data["disclosure_permission"]})
    with connect() as db: saved=db.execute("SELECT * FROM manager_look_through WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def manager_look_through(customer_id=None, manager_ref=None, fund_ref=None, disclosure_permission=None):
    with connect() as db:
        q="SELECT * FROM manager_look_through WHERE 1=1"; params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if manager_ref: q+=" AND manager_ref=?"; params.append(manager_ref)
        if fund_ref: q+=" AND fund_ref=?"; params.append(fund_ref)
        if disclosure_permission: q+=" AND disclosure_permission=?"; params.append(disclosure_permission)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def manager_look_through_export(customer_id=None, manager_ref=None, fund_ref=None):
    rows=manager_look_through(customer_id=customer_id,manager_ref=manager_ref,fund_ref=fund_ref)
    return {"generated_at":now(),"perimeter":{"customer_id":customer_id,"manager_ref":manager_ref,"fund_ref":fund_ref},"coverage":len(rows),"rows":rows}


FEE_SIMULATION_LEVELS=("manager","product","customer","total")

def save_fee_simulation(data):
    required=("customer_id","fund_ref","scenario_name","level","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["level"] not in FEE_SIMULATION_LEVELS: raise ValueError(f"level moet een van {', '.join(FEE_SIMULATION_LEVELS)} zijn")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",s).strip("-") for s in (str(data["customer_id"]),str(data["fund_ref"]),str(data["scenario_name"]),str(data["level"]))))
    pid=data.get("id") or f"feesim-{slug}"
    actor=data.get("actor","demo.client-service").strip() if str(data.get("actor","demo.client-service")).strip() else "demo.client-service"
    stamp=now(); cid=data["customer_id"]
    def opt(k):
        v=data.get(k); return (str(v).strip() if v is not None else None) or None
    def optf(k):
        v=data.get(k)
        if v is None or v=="": return None
        return float(v)
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM fee_simulation WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO fee_simulation(id,version,customer_id,fund_ref,manager_ref,product_ref,scenario_name,level,baseline_amount,scenario_amount,delta_amount,missing_inputs,uncertainty,source_ref,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,data["fund_ref"].strip(),opt("manager_ref"),opt("product_ref"),data["scenario_name"].strip(),data["level"].strip(),optf("baseline_amount"),optf("scenario_amount"),optf("delta_amount"),opt("missing_inputs"),opt("uncertainty"),data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"fee_simulation",pid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),{"customer_id":cid,"version":version,"level":data["level"]})
    with connect() as db: saved=db.execute("SELECT * FROM fee_simulation WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def fee_simulation(customer_id=None, fund_ref=None, level=None, manager_ref=None, product_ref=None):
    with connect() as db:
        q="SELECT * FROM fee_simulation WHERE 1=1"; params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if fund_ref: q+=" AND fund_ref=?"; params.append(fund_ref)
        if level: q+=" AND level=?"; params.append(level)
        if manager_ref: q+=" AND manager_ref=?"; params.append(manager_ref)
        if product_ref: q+=" AND product_ref=?"; params.append(product_ref)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def fee_simulation_export(customer_id=None, fund_ref=None, level=None):
    rows=fee_simulation(customer_id=customer_id,fund_ref=fund_ref,level=level)
    return {"generated_at":now(),"perimeter":{"customer_id":customer_id,"fund_ref":fund_ref,"level":level},"coverage":len(rows),"rows":rows}

# aliases
save_fee_simulations=save_fee_simulation
fee_simulations=fee_simulation
fee_simulations_export=fee_simulation_export

# TWIN-002 Isolatie en reproduceerbaarheid
import json as _json

def save_scenario_snapshot(data):
    required=("customer_id","scenario_name","snapshot","inputs","calc_logic_version","policy_version","schema_version")
    for key in required:
        if data.get(key) is None or (isinstance(data[key],str) and not data[key].strip()):
            raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",str(s).lower()).strip("-") for s in (data["customer_id"],data["scenario_name"])))
    pid=data.get("id") or f"scenario-{slug}"
    actor=data.get("actor","demo.client-service")
    if not str(actor).strip(): actor="demo.client-service"
    actor=str(actor).strip()
    stamp=now(); cid=data["customer_id"]
    snapshot=data["snapshot"]
    inputs=data["inputs"]
    if not isinstance(snapshot,(dict,list,str)): raise ValueError("snapshot ongeldig")
    if not isinstance(inputs,(dict,list,str)): raise ValueError("inputs ongeldig")
    snapshot_json=snapshot if isinstance(snapshot,str) else _json.dumps(snapshot,sort_keys=True)
    inputs_json=inputs if isinstance(inputs,str) else _json.dumps(inputs,sort_keys=True)
    # deterministic outcome derived from snapshot+inputs+versions (reproducible)
    outcome=_json.dumps({"snapshot":snapshot_json,"inputs":inputs_json,
        "calc_logic_version":data["calc_logic_version"],"policy_version":data["policy_version"],
        "schema_version":data["schema_version"]},sort_keys=True)
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM scenario_snapshots WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO scenario_snapshots(id,version,customer_id,scenario_name,snapshot,inputs,calc_logic_version,policy_version,schema_version,outcome,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,data["scenario_name"].strip() if isinstance(data["scenario_name"],str) else str(data["scenario_name"]),snapshot_json,inputs_json,
           str(data["calc_logic_version"]).strip(),str(data["policy_version"]).strip(),str(data["schema_version"]).strip(),outcome,actor,stamp))
        audit(db,"scenario_snapshot",pid,"created" if version==1 else "versioned",actor,"scenario snapshot",{"customer_id":cid,"version":version})
    with connect() as db: saved=db.execute("SELECT * FROM scenario_snapshots WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def scenario_snapshots(customer_id=None, scenario_name=None):
    with connect() as db:
        q="SELECT * FROM scenario_snapshots WHERE 1=1"; params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if scenario_name: q+=" AND scenario_name=?"; params.append(scenario_name)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def scenario_snapshot_export(customer_id=None, scenario_name=None):
    rows=scenario_snapshots(customer_id=customer_id,scenario_name=scenario_name)
    return {"generated_at":now(),"perimeter":{"customer_id":customer_id,"scenario_name":scenario_name},"coverage":len(rows),"rows":rows}

# aliases
save_scenario_snapshots=save_scenario_snapshot
scenario_snapshot=scenario_snapshots
wtp_risk_controls = wtp_risks
wtp_changes = wtp_risks
save_wtp_change = save_wtp_risk
def fee_components_export(customer_id=None, fund_ref=None):
    rows=fee_components(customer_id=customer_id,fund_ref=fund_ref)
    return {"generated_at":now(),"perimeter":{"customer_id":customer_id,"fund_ref":fund_ref},
           "coverage":len(rows),"rows":rows}
wtp_transition_risks = wtp_risks
save_wtp_transition_risk = save_wtp_risk

def snapshot_graph_knowledge(db, customer_id, actor, reason, stamp=None):
    stamp=stamp or now()
    entities=[dict(r) for r in db.execute('''SELECT e.* FROM client_entities e JOIN
      (SELECT id,MAX(version) version FROM client_entities WHERE customer_id=? GROUP BY id) latest
      ON e.id=latest.id AND e.version=latest.version ORDER BY e.entity_type,e.name''',(customer_id,)).fetchall()]
    relationships=[dict(r) for r in db.execute('''SELECT r.* FROM client_relationships r JOIN
      (SELECT id,MAX(version) version FROM client_relationships WHERE customer_id=? GROUP BY id) latest
      ON r.id=latest.id AND r.version=latest.version ORDER BY r.created_at DESC''',(customer_id,)).fetchall()]
    requirements=[dict(r) for r in db.execute("SELECT * FROM client_requirements WHERE customer_id=? ORDER BY id,version",(customer_id,)).fetchall()]
    revision=db.execute("SELECT COALESCE(MAX(revision),0)+1 FROM graph_knowledge_snapshots WHERE customer_id=?",(customer_id,)).fetchone()[0]
    timeline={"entities":entities,"relationships":relationships,"requirements":requirements}
    db.execute("INSERT INTO graph_knowledge_snapshots VALUES(?,?,?,?,?,?,?)",(str(uuid.uuid4()),customer_id,revision,stamp,actor,reason,json.dumps(timeline,sort_keys=True)))
    audit(db,"client_graph",customer_id,"snapshot_captured",actor,reason,{"revision":revision,"recorded_at":stamp,"entities":len(entities),"relationships":len(relationships),"requirements":len(requirements)})
    return revision

def graph_knowledge_history(customer_id):
    with connect() as db: rows=db.execute("SELECT revision,recorded_at,actor,reason,timeline FROM graph_knowledge_snapshots WHERE customer_id=? ORDER BY revision DESC",(customer_id,)).fetchall()
    return [{"revision":r["revision"],"recorded_at":r["recorded_at"],"actor":r["actor"],"reason":r["reason"],"entities":len(json.loads(r["timeline"]).get("entities",[])),"relationships":len(json.loads(r["timeline"]).get("relationships",[])),"requirements":len(json.loads(r["timeline"]).get("requirements",[]))} for r in rows]

def client_graph(customer_id, valid_at=None, known_at=None):
    valid_at=valid_at or datetime.now(timezone.utc).date().isoformat()
    known_at=_utc_stamp(known_at or now())
    root=customer(customer_id,valid_at,known_at)
    if not root:return []
    with connect() as db:
        snapshot=db.execute("SELECT * FROM graph_knowledge_snapshots WHERE customer_id=? AND recorded_at<=? ORDER BY recorded_at DESC,revision DESC LIMIT 1",(customer_id,known_at)).fetchone()
    timeline=json.loads(snapshot["timeline"]) if snapshot else {"entities":[],"relationships":[]}
    entities=[e for e in timeline["entities"] if e["effective_from"]<=valid_at and (not e["effective_to"] or e["effective_to"]>valid_at)]
    client_root={"id":customer_id,"version":root["version"],"customer_id":customer_id,"entity_type":"customer","name":root["name"],"legal_identifier":"","jurisdiction":root["jurisdiction"],"classification":root["classification"],"effective_from":root["valid_from"],"effective_to":None,"source_ref":"Customer register","rationale":"Read-only root from the customer master record.","created_by":"customer-master","created_at":root["recorded_from"],"read_only":True}
    entity_map={e["id"]:e["name"] for e in [client_root]+entities}
    relationships=[]
    for rel in timeline["relationships"]:
        if rel["effective_from"]<=valid_at and (not rel["effective_to"] or rel["effective_to"]>valid_at):
            rel["from_name"]=entity_map.get(rel["from_entity_id"],"(entiteit niet actief op geldigheidsdatum)")
            rel["to_name"]=entity_map.get(rel["to_entity_id"],"(entiteit niet actief op geldigheidsdatum)")
            relationships.append(rel)
    return {"customer_id":customer_id,"valid_at":valid_at,"known_at":snapshot["recorded_at"] if snapshot else None,"snapshot_revision":snapshot["revision"] if snapshot else None,"entities":[client_root]+entities,"relationships":relationships}

def client_entities(customer_id, valid_at=None, known_at=None):
    graph=client_graph(customer_id,valid_at,known_at)
    return graph["entities"] if graph else []

def save_client_entity(data):
    required=("customer_id","entity_type","name","jurisdiction","classification","effective_from","source_ref","rationale")
    for key in required:
        if not str(data.get(key,"")).strip():raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]):raise ValueError("Klant niet gevonden")
    allowed={"customer","legal_entity","group","fund","fiduciary","asset_manager","sub_manager","custodian","service_provider","other"}
    if data["entity_type"] not in allowed:raise ValueError("Ongeldig entiteitstype")
    try:date.fromisoformat(data["effective_from"]); date.fromisoformat(data["effective_to"]) if data.get("effective_to") else None
    except ValueError:raise ValueError("Geldigheidsdatum moet ISO-formaat YYYY-MM-DD hebben")
    legal_id=(data.get("legal_identifier") or "").strip()
    # Legal identifiers are optional for synthetic/prototype records. No personal data belongs here.
    if data.get("effective_to") and data["effective_to"]<=data["effective_from"]:raise ValueError("Einddatum moet na de ingangsdatum liggen")
    effective_to=data.get("effective_to") or None
    eid=data.get("id") or str(uuid.uuid4()); actor=data.get("actor","demo.client-service").strip(); stamp=now()
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM client_entities WHERE id=? AND customer_id=?",(eid,data["customer_id"])).fetchone()["version"]
        if previous is None and data.get("id"):raise ValueError("Entiteit voor deze klant niet gevonden")
        version=(previous or 0)+1
        db.execute("INSERT INTO client_entities VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(eid,version,data["customer_id"],data["entity_type"],data["name"].strip(),legal_id,data["jurisdiction"].strip(),data["classification"].strip(),data["effective_from"],effective_to,data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"client_entity",eid,"created" if version==1 else "versioned",actor,data["rationale"],{"customer_id":data["customer_id"],"version":version,"entity_type":data["entity_type"],"source_ref":data["source_ref"].strip(),"effective_from":data["effective_from"],"effective_to":effective_to})
        snapshot_graph_knowledge(db,data["customer_id"],actor,data["rationale"],stamp)
    with connect() as db: saved=db.execute("SELECT * FROM client_entities WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(eid,data["customer_id"])).fetchone()
    return dict(saved)

def client_relationships(customer_id, valid_at=None, known_at=None):
    graph=client_graph(customer_id,valid_at,known_at)
    return graph["relationships"] if graph else []

def save_client_relationship(data):
    required=("customer_id","from_entity_id","to_entity_id","relationship_type","service_scope","effective_from","source_ref","rationale")
    for key in required:
        if not str(data.get(key,"")).strip():raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]):raise ValueError("Klant niet gevonden")
    if data["from_entity_id"]==data["to_entity_id"]:raise ValueError("Een relatie kan niet naar dezelfde entiteit verwijzen")
    allowed={"member_of_group","parent_of","fiduciary_for","manages","subdelegates_to","custody_for","service_provider_for","client_of"}
    if data["relationship_type"] not in allowed:raise ValueError("Ongeldig relatietype")
    try:date.fromisoformat(data["effective_from"]); date.fromisoformat(data["effective_to"]) if data.get("effective_to") else None
    except ValueError:raise ValueError("Geldigheidsdatum moet ISO-formaat YYYY-MM-DD hebben")
    entities={e["id"] for e in client_entities(data["customer_id"])}
    if data["from_entity_id"] not in entities or data["to_entity_id"] not in entities:raise ValueError("Beide relatie-entiteiten moeten binnen dezelfde klantconfiguratie bestaan")
    if data.get("effective_to") and data["effective_to"]<=data["effective_from"]:raise ValueError("Einddatum moet na de ingangsdatum liggen")
    effective_to=data.get("effective_to") or None
    rid=data.get("id") or str(uuid.uuid4());actor=data.get("actor","demo.client-service").strip();stamp=now()
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM client_relationships WHERE id=? AND customer_id=?",(rid,data["customer_id"])).fetchone()["version"]
        if previous is None and data.get("id"):raise ValueError("Relatie voor deze klant niet gevonden")
        version=(previous or 0)+1
        db.execute("INSERT INTO client_relationships VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(rid,version,data["customer_id"],data["from_entity_id"],data["to_entity_id"],data["relationship_type"],data["service_scope"].strip(),data["effective_from"],effective_to,data["source_ref"].strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"client_relationship",rid,"created" if version==1 else "versioned",actor,data["rationale"],{"customer_id":data["customer_id"],"version":version,"from_entity_id":data["from_entity_id"],"to_entity_id":data["to_entity_id"],"relationship_type":data["relationship_type"],"source_ref":data["source_ref"].strip(),"effective_from":data["effective_from"],"effective_to":effective_to})
        snapshot_graph_knowledge(db,data["customer_id"],actor,data["rationale"],stamp)
    with connect() as db: saved=db.execute("SELECT * FROM client_relationships WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(rid,data["customer_id"])).fetchone()
    return dict(saved)

def policies(control_code=None, valid_at=None, known_at=None):
    if valid_at is not None and known_at is not None:
        rows=policies_as_of(valid_at,known_at,control_code=control_code)
        return rows
    with connect() as db:
        if control_code:
            rows=db.execute("SELECT * FROM policy_controls WHERE control_code=? ORDER BY version DESC",(control_code,)).fetchall()
        else:
            rows=db.execute("SELECT p.* FROM policy_controls p JOIN (SELECT control_code,MAX(version) AS version FROM policy_controls GROUP BY control_code) latest ON p.control_code=latest.control_code AND p.version=latest.version ORDER BY p.control_code").fetchall()
    result=[]
    with connect() as db:
        for row in rows:
            item=dict(row)
            review=db.execute("SELECT * FROM policy_source_reviews WHERE control_code=? AND policy_version=? ORDER BY checked_at DESC LIMIT 1",(item["control_code"],item["version"])).fetchone()
            decision=db.execute("SELECT * FROM policy_decisions WHERE control_code=? AND policy_version=? ORDER BY decided_at DESC LIMIT 1",(item["control_code"],item["version"])).fetchone()
            item["latest_source_review"]=dict(review) if review else None
            item["decision"]=dict(decision) if decision else None
            item["validation_status"]=(decision["decision"] if decision else "pending")
            if decision and decision["decision"]=="validated" and review and review["checked_at"]>decision["decided_at"]:
                item["validation_status"]="pending"
            result.append(item)
    return result

def policies_as_of(valid_at, known_at, control_code=None):
    """Return policy versions effective at valid_at and recorded by known_at."""
    valid_at = valid_at or datetime.now(timezone.utc).date().isoformat()
    known_stamp=_utc_stamp(known_at or now())
    with connect() as db:
        rows=db.execute("SELECT * FROM policy_controls WHERE created_at<=? ORDER BY control_code,effective_date,version",(known_stamp,)).fetchall()
    grouped={}
    for row in rows:
        item=dict(row)
        if item["control_code"] and control_code and item["control_code"]!=control_code.strip().upper():
            continue
        if valid_at is None or item["effective_date"]<=valid_at:
            prior=grouped.get(item["control_code"])
            if not prior or (item["effective_date"],item["version"])>(prior["effective_date"],prior["version"]):
                grouped[item["control_code"]]=item
    result=[]
    with connect() as db:
        for item in grouped.values():
            review=db.execute("SELECT * FROM policy_source_reviews WHERE control_code=? AND policy_version=? AND checked_at<=? ORDER BY checked_at DESC LIMIT 1",(item["control_code"],item["version"],known_stamp)).fetchone()
            decision=db.execute("SELECT * FROM policy_decisions WHERE control_code=? AND policy_version=? AND decided_at<=? ORDER BY decided_at DESC LIMIT 1",(item["control_code"],item["version"],known_stamp)).fetchone()
            item["latest_source_review"]=dict(review) if review else None
            item["decision"]=dict(decision) if decision else None
            item["validation_status"]=(decision["decision"] if decision else "pending")
            if decision and decision["decision"]=="validated" and review and review["checked_at"]>decision["decided_at"]: item["validation_status"]="pending"
            item["valid_at"]=valid_at; item["known_at"]=known_stamp
            result.append(item)
    return sorted(result,key=lambda policy:policy["control_code"])

def hard_block(control_code, version=None):
    """Evaluate whether a policy control may act as a hard block.

    A hard block is REFUSED (ValueError) unless the control has enforcement
    level ``hard``, a derived validation status of ``validated`` and evidence:
    a validated policy decision that cites a source review plus a rationale.
    Soft/manual controls never block by design.
    """
    items = policies(control_code)
    if not items: raise ValueError("Policycontrol niet gevonden")
    policy = items[0] if version is None else next((p for p in items if p["version"]==int(version)),None)
    if not policy: raise ValueError(f"Policyversie {version} van {control_code} niet gevonden")
    if policy["enforcement"]!="hard":
        return {"control_code":policy["control_code"],"version":policy["version"],"blocking":False,"reason":"Handhavingsniveau is niet hard; dit control blokkeert nooit"}
    if policy["validation_status"]!="validated":
        raise ValueError("Harde blokkade geweigerd: validatiestatus is niet 'validated' (te valideren door Compliance/Legal)")
    decision=policy["decision"]
    if not decision or not decision.get("source_review_id") or not str(decision.get("rationale","")).strip():
        raise ValueError("Harde blokkade geweigerd: geen bewijs in de vorm van een gevalideerd besluit met geverifieerde bronreview en motivering")
    return {"control_code":policy["control_code"],"version":policy["version"],"blocking":True,"decision_id":decision["id"],"source_review_id":decision["source_review_id"]}

def policy_signals():
    """Non-blocking signals for policy controls that are not (yet) validated.

    Unapproved interpretations must surface as signals, never as hard blocks:
    every control whose derived validation status is not 'validated' — plus
    every control past its review date — yields a severity='signal' entry.
    """
    signals=[]
    today=datetime.now(timezone.utc).date().isoformat()
    for p in policies():
        if p["validation_status"]!="validated":
            signals.append({"control_code":p["control_code"],"version":p["version"],"enforcement":p["enforcement"],"severity":"signal","code":"POLICY_NOT_VALIDATED","message":"Interpretatie nog niet gevalideerd via bronreview en besluit; dit is een niet-blokkerend signaal.","blocking":False})
        if p["review_date"]<=today:
            signals.append({"control_code":p["control_code"],"version":p["version"],"enforcement":p["enforcement"],"severity":"signal","code":"POLICY_REVIEW_DUE","message":f"Reviewdatum {p['review_date']} is verstreken; menselijke review vereist.","blocking":False})
    return signals

def save_policy(data, control_code=None):
    required=("control_code","title","owner","audience","source_ref","applicability","enforcement","effective_date","review_date")
    if not control_code and not data.get("control_code","").strip(): raise ValueError("Controlcode is verplicht")
    for key in required[1:]:
        if not str(data.get(key,"")).strip(): raise ValueError(f"{key.replace('_',' ').capitalize()} is verplicht")
    try:
        from datetime import date
        effective=date.fromisoformat(data["effective_date"]); review=date.fromisoformat(data["review_date"])
    except ValueError: raise ValueError("Effectieve datum en reviewdatum moeten geldige ISO-datums zijn")
    if review < effective: raise ValueError("Reviewdatum mag niet voor de ingangsdatum liggen")
    enforcement=data["enforcement"]
    status=data.get("validation_status","pending")
    evidence=data.get("validation_evidence","").strip()
    if enforcement not in {"hard","soft","manual"}: raise ValueError("Handhavingsniveau moet hard, soft of manual zijn")
    if status!="pending": raise ValueError("Validatiestatus wordt uitsluitend via de bronreview- en besluitworkflow vastgesteld")
    code=(control_code or data["control_code"]).strip().upper()
    actor=data.get("actor","demo.policy-owner").strip() or "demo.policy-owner"
    note=data.get("change_note","").strip() or ("Eerste registratie" if not control_code else "Nieuwe append-only versie")
    with connect() as db:
        previous=db.execute("SELECT MAX(version) AS version FROM policy_controls WHERE control_code=?",(code,)).fetchone()["version"]
        if control_code and previous is None: raise ValueError("Controlcode niet gevonden")
        if not control_code and previous is not None: raise ValueError("Controlcode bestaat al; maak een nieuwe versie")
        version=(previous or 0)+1; stamp=now(); record_id=str(uuid.uuid4())
        db.execute("INSERT INTO policy_controls VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(record_id,code,version,data["title"].strip(),data["owner"].strip(),data["audience"].strip(),data["source_ref"].strip(),data["applicability"].strip(),enforcement,data["effective_date"],data["review_date"],status,evidence,actor,stamp,note))
        audit(db,"policy_control",record_id,"created" if version==1 else "versioned",actor,note,{"control_code":code,"version":version,"validation_status":status,"enforcement":enforcement},policy_version=str(version),evidence=note)
    return policies(code)[0]

def policy_source_reviews(control_code,version):
    with connect() as db:
        exists=db.execute("SELECT 1 FROM policy_controls WHERE control_code=? AND version=?",(control_code,version)).fetchone()
        if not exists:return None
        rows=db.execute("SELECT * FROM policy_source_reviews WHERE control_code=? AND policy_version=? ORDER BY checked_at DESC",(control_code,version)).fetchall()
    return [dict(r) for r in rows]

def add_policy_source_review(control_code,version,data):
    versions=policies(control_code)
    policy=next((p for p in versions if p["version"]==int(version)),None)
    if not policy:raise ValueError("Policyversie niet gevonden")
    kind=data.get("source_kind",""); outcome=data.get("outcome","")
    allowed_kinds={"primary_regulatory","customer_contract","customer_policy","secondary_guidance","user_claim","generated"}
    if kind not in allowed_kinds:raise ValueError("Onbekende bronsoort")
    if outcome not in {"verified","insufficient","pending"}:raise ValueError("Ongeldige bronreview-uitkomst")
    if not data.get("source_title","").strip() or not data.get("source_locator","").strip() or not data.get("rationale","").strip():raise ValueError("Bronnaam, bronreferentie en reviewmotivering zijn verplicht")
    if outcome=="verified" and kind not in {"primary_regulatory","customer_contract","customer_policy"}:
        raise ValueError("Alleen een primaire bron, klantcontract of vastgesteld klantbeleid kan als gevalideerde bron gelden")
    actor=data.get("reviewer","demo.source-reviewer").strip(); role=data.get("reviewer_role","")
    if not actor:raise ValueError("Reviewer is verplicht")
    if role not in {"compliance","legal","policy_owner"}:raise ValueError("Reviewerrol moet Compliance, Legal of policy-eigenaar zijn")
    if outcome=="verified" and actor==policy["created_by"]:raise ValueError("Bronverificatie vereist een andere reviewer dan de initiator")
    review_id=str(uuid.uuid4()); stamp=now()
    with connect() as db:
        db.execute("INSERT INTO policy_source_reviews VALUES(?,?,?,?,?,?,?,?,?,?,?)",(review_id,control_code,int(version),kind,data["source_title"].strip(),data["source_locator"].strip(),outcome,actor,role,data["rationale"].strip(),stamp))
        audit(db,"policy_source_review",review_id,"source_reviewed",actor,data["rationale"],{"control_code":control_code,"version":int(version),"source_kind":kind,"outcome":outcome})
    return policy_source_reviews(control_code,version)

def decide_policy(control_code,version,data):
    versions=policies(control_code); policy=next((p for p in versions if p["version"]==int(version)),None)
    if not policy:raise ValueError("Policyversie niet gevonden")
    decision=data.get("decision","validated"); actor=data.get("reviewer","demo.policy-approver").strip(); role=data.get("reviewer_role","")
    rationale=data.get("rationale","").strip()
    if decision not in {"validated","rejected"}:raise ValueError("Besluit moet validated of rejected zijn")
    if role not in {"compliance","legal","policy_owner"}:raise ValueError("Reviewerrol moet Compliance, Legal of policy-eigenaar zijn")
    if not actor or not rationale:raise ValueError("Beslisser en motivering zijn verplicht")
    if actor==policy["created_by"]:raise ValueError("Policybesluit vereist een andere persoon dan de initiator")
    review=policy["latest_source_review"]
    if decision=="validated":
        if not review or review["outcome"]!="verified":raise ValueError("Valideren vereist eerst een geverifieerde primaire bron of klantbron")
        if actor==review["reviewer"]:raise ValueError("Policybesluit vereist een andere reviewer dan de bronreviewer")
        if role in {"compliance","legal"} and review["reviewer_role"] in {"compliance","legal"} and actor==review["reviewer"]:raise ValueError("Policyvalidatie en bronreview moeten door verschillende personen worden uitgevoerd")
    decision_id=str(uuid.uuid4()); stamp=now()
    with connect() as db:
        db.execute("INSERT INTO policy_decisions VALUES(?,?,?,?,?,?,?,?,?)",(decision_id,control_code,int(version),review["id"] if review else None,decision,actor,role,rationale,stamp))
        audit(db,"policy_control",policy["id"],"policy_decision",actor,rationale,{"control_code":control_code,"version":int(version),"decision":decision,"source_review_id":review["id"] if review else None},policy_version=str(int(version)),evidence=review["id"] if review else rationale)
    return policies(control_code)
init()


def client_variants(control_code=None, client_id=None):
    with connect() as db:
        q="SELECT * FROM client_variants"
        params=[]
        conds=[]
        if control_code:
            conds.append("control_code=?"); params.append(control_code)
        if client_id:
            conds.append("client_id=?"); params.append(client_id)
        if conds:
            q+=" WHERE "+" AND ".join(conds)
        q+=" ORDER BY created_at DESC"
        rows=db.execute(q,tuple(params)).fetchall()
    return [dict(r) for r in rows]


def save_client_variant(data):
    required=("control_code","policy_version","client_id","contractual_requirement","source_ref","reconciliation_status","effective_date","owner","rationale")
    for key in required:
        if not str(data.get(key,"")).strip():
            raise ValueError(f"{key} is verplicht")
    if data["reconciliation_status"] not in {"configured_match","configuration_gap","unmapped","manual_review"}:
        # manual reconciliation status may be any non-empty label? accept manual labels too
        pass
    # FK check
    with connect() as db:
        exists=db.execute("SELECT 1 FROM policy_controls WHERE control_code=? AND version=?", (data["control_code"], int(data["policy_version"]))).fetchone()
    if not exists:
        raise ValueError("Policy control versie niet gevonden")
    variant_id=data.get("id") or str(uuid.uuid4())
    actor=data.get("actor","demo.client-service").strip() or "demo.client-service"
    stamp=now()
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM client_variants WHERE id=?",(variant_id,)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("INSERT INTO client_variants VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (variant_id,version,data["control_code"].strip(),int(data["policy_version"]),data["client_id"].strip(),(data.get("fund_id") or "").strip() or None,
             data["contractual_requirement"].strip(),data["source_ref"].strip(),data["reconciliation_status"].strip(),
             data["effective_date"],data["owner"].strip(),actor,stamp,data["rationale"].strip()))
        audit(db,"client_variant",variant_id,"created" if version==1 else "versioned",actor,data["rationale"],
            {"control_code":data["control_code"],"version":version,"client_id":data["client_id"],"reconciliation_status":data["reconciliation_status"]})
    return next(r for r in client_variants() if r["id"]==variant_id and r["version"]==version)


def set_reconciliation_status(variant_id, status, actor, rationale):
    rows=client_variants()
    current=[r for r in rows if r["id"]==variant_id]
    if not current:
        raise ValueError("Variant niet gevonden")
    current=sorted(current,key=lambda r:r["version"])[-1]
    data={
        "id":variant_id,"control_code":current["control_code"],"policy_version":current["policy_version"],
        "client_id":current["client_id"],"fund_id":current["fund_id"],
        "contractual_requirement":current["contractual_requirement"],"source_ref":current["source_ref"],
        "reconciliation_status":status,"effective_date":current["effective_date"],"owner":current["owner"],
        "rationale":rationale,"actor":actor,
    }
    return save_client_variant(data)


def client_variant_signals(control_code=None):
    # non-blocking signals for unapproved interpretations
    result=[]
    for v in client_variants(control_code):
        pols=[p for p in __import__("app.store",fromlist=["x"]).policies(v["control_code"]) if p["version"]==v["policy_version"]]
        status=pols[0]["validation_status"] if pols else "pending"
        if status!="validated":
            result.append({"variant_id":v["id"],"control_code":v["control_code"],"signal":"policy_not_validated","blocking":False})
    return result

# DOC-001: versiegebonden bewijsreferenties — documentmetadata, geen bestandsinhoud.
DOCUMENT_TYPES={"contract","policy","isms_certificate","assessment_report","minutes","other"}
CONFIDENTIALITY_CLASSES={"open","intern","vertrouwelijk","geheim"}
RETENTION_CLASSES={"default_7y","default_10y","permanent","custom"}

def document_references(subject_type=None, subject_id=None, subject_version=None):
    query="SELECT d.* FROM document_references d JOIN (SELECT id,MAX(version) version FROM document_references GROUP BY id) latest ON d.id=latest.id AND d.version=latest.version"
    clauses=[]; args=[]
    if subject_type: clauses.append("d.subject_type=?"); args.append(subject_type)
    if subject_id: clauses.append("d.subject_id=?"); args.append(subject_id)
    if subject_version is not None:
        clauses.append("d.subject_version=?"); args.append(subject_version)
    if clauses: query+=" WHERE "+" AND ".join(clauses)
    query+=" ORDER BY d.created_at DESC"
    with connect() as db: rows=db.execute(query,args).fetchall()
    return [dict(row) for row in rows]

def save_document_reference(data):
    unknown={"content","file_path","blob"} & {k for k in data if data.get(k)}
    if unknown: raise ValueError("Documentinhoud wordt niet opgeslagen; alleen referenties (DOC-001: geen contractbestand of klantgegeven in git)")
    required=("subject_type","subject_id","subject_version","document_type","document_date","owner","confidentiality","retention_class","storage_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if data["document_type"] not in DOCUMENT_TYPES: raise ValueError("Ongeldig documenttype")
    if data["confidentiality"] not in CONFIDENTIALITY_CLASSES: raise ValueError("Ongeldige vertrouwelijkheidsklasse")
    if data["retention_class"] not in RETENTION_CLASSES: raise ValueError("Ongeldige retentieklasse")
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",data["document_date"]): raise ValueError
        date.fromisoformat(data["document_date"])
    except ValueError: raise ValueError("Documentdatum moet ISO YYYY-MM-DD zijn")
    subject_version=data["subject_version"]
    if isinstance(subject_version,bool) or not isinstance(subject_version,int) or subject_version<1: raise ValueError("subject_version moet een positief geheel getal zijn")
    storage_ref=data["storage_ref"].strip()
    scheme=storage_ref.split("://",1)[0].lower() if "://" in storage_ref else ""
    if scheme not in {"dms","s3","https","azblob","gs"}: raise ValueError("storage_ref moet een externe opslagreferentie zijn (bijv. dms://, s3://, https://); lokale bestanden en inhoud worden niet bewaard")
    # Identiteit is de (subject, documenttype)-binding; revisies vormen append-only versies van dezelfde referentie.
    ref_id=data.get("id") or "docref-"+re.sub(r"[^a-z0-9]+","-",f"{data['subject_type'].strip()}-{data['subject_id'].strip()}-{data['document_type']}".lower()).strip("-")
    actor=data.get("actor","demo.compliance").strip(); stamp=now()
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM document_references WHERE id=?",(ref_id,)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("INSERT INTO document_references(id,version,subject_type,subject_id,subject_version,document_type,document_date,owner,confidentiality,retention_class,storage_ref,rationale,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(ref_id,version,data["subject_type"].strip(),data["subject_id"].strip(),subject_version,data["document_type"],data["document_date"],data["owner"].strip(),data["confidentiality"],data["retention_class"],storage_ref,data["rationale"].strip(),actor,stamp))
        audit(db,"document_reference",ref_id,"created" if version==1 else "versioned",actor,data["rationale"],{"version":version,"subject_type":data["subject_type"],"subject_id":data["subject_id"],"subject_version":subject_version,"document_type":data["document_type"],"document_date":data["document_date"],"owner":data["owner"],"confidentiality":data["confidentiality"],"retention_class":data["retention_class"],"storage_ref":storage_ref})
    return next(r for r in document_references(subject_id=data["subject_id"]) if r["id"]==ref_id)

# OUT-001: Activiteitregister — per relatie werkzaamheden, grenzen, diensten,
# fonds-/mandaatrelatie, kritikaliteit/materialiteit, eigenaar en contractperiode.
ACTIVITY_CRITICALITY={"laag","gemiddeld","hoog"}
ACTIVITY_MATERIALITY={"immatérieel","materieel","zeer materieel"}

def activities(customer_id=None, valid_at=None, known_at=None):
    if valid_at is not None and known_at is not None:
        return _activities_as_of(customer_id,valid_at,known_at)
    query="SELECT a.* FROM activity_register a JOIN (SELECT id,MAX(version) version FROM activity_register GROUP BY id) latest ON a.id=latest.id AND a.version=latest.version"
    clauses=[];args=[]
    if customer_id: clauses.append("a.customer_id=?");args.append(customer_id)
    if clauses: query+=" WHERE "+" AND ".join(clauses)
    query+=" ORDER BY a.created_at DESC"
    with connect() as db: rows=db.execute(query,args).fetchall()
    result=[]
    for row in rows:
        item=dict(row); item["services"]=json.loads(item["services"])
        if item["fund_mandate_ref"] is None: item["fund_mandate_ref"]=""
        result.append(item)
    return result

def _activities_as_of(customer_id,valid_at,known_at):
    valid_at=valid_at or datetime.now(timezone.utc).date().isoformat()
    known_stamp=_utc_stamp(known_at or now())
    query="SELECT * FROM activity_register WHERE created_at<=?"
    clauses=[];args=[known_stamp]
    if customer_id: clauses.append("customer_id=?");args.append(customer_id)
    if clauses: query+=" AND "+" AND ".join(clauses)
    query+=" ORDER BY id,version"
    with connect() as db: rows=db.execute(query,args).fetchall()
    grouped={}
    for row in rows:
        item=dict(row)
        if item["effective_from"]>valid_at: continue
        if item["effective_to"] and item["effective_to"]<=valid_at: continue
        prior=grouped.get(item["id"])
        if not prior or item["version"]>prior["version"]: grouped[item["id"]]=item
    result=[]
    for item in grouped.values():
        item["services"]=json.loads(item["services"])
        if item["fund_mandate_ref"] is None: item["fund_mandate_ref"]=""
        result.append(item)
    return sorted(result,key=lambda a:(a["activity_code"],a["id"]))

def save_activity(data):
    required=("customer_id","activity_code","title","description","boundaries","services","fund_mandate_ref","criticality","materiality","owner","contract_start","source_ref","rationale","effective_from")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["criticality"] not in ACTIVITY_CRITICALITY: raise ValueError("Kritikaliteit moet laag, gemiddeld of hoog zijn")
    if data["materiality"] not in ACTIVITY_MATERIALITY: raise ValueError("Materialiteit moet immatérieel, materieel of zeer materieel zijn")
    services=data["services"]
    if isinstance(services,str):
        try: services=json.loads(services)
        except ValueError: services=[s.strip() for s in services.split(",") if s.strip()]
    if not isinstance(services,list) or not services or not all(isinstance(s,str) and s.strip() for s in services): raise ValueError("services moet een niet-lege lijst met dienstnamen zijn")
    try:
        date.fromisoformat(data["effective_from"]); date.fromisoformat(data["contract_start"])
        if data.get("contract_end"): date.fromisoformat(data["contract_end"])
    except ValueError: raise ValueError("Geldigheids- en contractdatums moeten ISO-formaat YYYY-MM-DD hebben")
    if data.get("contract_end") and data["contract_end"]<data["contract_start"]: raise ValueError("Contracteind moet op of na de contractstart liggen")
    aid=data.get("id") or "act-"+re.sub(r"[^a-z0-9]+","-",f"{data['customer_id']}-{data['activity_code']}".lower()).strip("-")
    actor=data.get("actor","demo.client-service").strip(); stamp=now()
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM activity_register WHERE id=? AND customer_id=?",(aid,data["customer_id"])).fetchone()["version"]
        if previous is None and data.get("id"): raise ValueError("Activiteit voor deze klant niet gevonden")
        version=(previous or 0)+1
        db.execute("INSERT INTO activity_register VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(aid,version,data["customer_id"],data["activity_code"].strip(),data["title"].strip(),data["description"].strip(),data["boundaries"].strip(),json.dumps(services),data["fund_mandate_ref"].strip(),data["criticality"],data["materiality"],data["owner"].strip(),data["contract_start"],data.get("contract_end") or None,data["source_ref"].strip(),data["effective_from"],data.get("effective_to") or None,data["rationale"].strip(),actor,stamp))
        audit(db,"activity_register",aid,"created" if version==1 else "versioned",actor,data["rationale"],{"customer_id":data["customer_id"],"version":version,"activity_code":data["activity_code"],"owner":data["owner"],"services":services,"criticality":data["criticality"],"materiality":data["materiality"],"contract_start":data["contract_start"],"contract_end":data.get("contract_end")})
    with connect() as db: saved=db.execute("SELECT * FROM activity_register WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(aid,data["customer_id"])).fetchone()
    item=dict(saved); item["services"]=json.loads(item["services"])
    return item

def activity_chain(customer_id,activity_id,valid_at=None,known_at=None):
    """Volledige keten voor een fonds-/mandaatwijziging: activiteit, diensten,
    afhankelijkheden (relaties/DORA-assessments), missende contractvelden en
    review-/meldstatus. Thresholds en statussen zijn signals, geen blokkades."""
    rows=activities(customer_id=customer_id,valid_at=valid_at,known_at=known_at)
    match=[a for a in rows if a["id"]==activity_id]
    if not match: raise ValueError("Activiteit niet gevonden voor deze klant")
    activity=match[0]
    missing=[f for f in ("owner","contract_start","contract_end","fund_mandate_ref") if not str(activity.get(f) or "").strip()]
    dependencies={"entity_relationships":[],"dora_assessments":[]}
    try:
        dependencies["entity_relationships"]=[r for r in client_relationships(customer_id,valid_at=valid_at,known_at=known_at) if activity["activity_code"].lower() in str(r.get("service_scope","")).lower()]
    except Exception: pass
    try:
        dependencies["dora_assessments"]=[d for d in dora_assessments(valid_at=valid_at,known_at=known_at,customer_id=customer_id) if d.get("service_name") in activity["services"]]
    except Exception: pass
    # Review-/meldstatus: zonder gevalideerde Compliance/Legal-beoordeling is dit
    # een open gate — pending, nooit geclaimd compleet.
    review_status="pending"
    return {"customer_id":customer_id,"activity":activity,"services":activity["services"],
            "fund_mandate_ref":activity["fund_mandate_ref"],"missing_contract_fields":missing,
            "dependencies":dependencies,"review_status":review_status,
            "validation_note":"te valideren door Compliance/Legal voor relevante klant/partij"}

# OUT-002: Ketenregister — directe en indirecte aanbieders, diensten, datastromen,
# geografische/juridische entiteiten, contractrelaties en onderuitbesteders.
# Wijziging van een schakel identificeert geraakte klanten/mandaten.
CHAIN_PARTY_TYPES={"direct","indirect","subcontractor"}
# Thresholds zijn bronverwijzingen/policyparameters, nooit universeel hardcoded:
# de DNB-verwachting rond 30% onderuitbesteding staat hier als geparametriseerde
# bronvermelding die per klant/party kan worden overschreven.
CHAIN_THRESHOLD_DEFAULTS={"subcontract_share_pct":None,
    "source_ref":"DNB-verwachting 30% onderuitbesteding (bronvermelding); klantspecifiek te bevestigen door Compliance/Legal"}

def _chain_rows(customer_id,valid_at,known_at):
    valid_at=valid_at or datetime.now(timezone.utc).date().isoformat()
    known_stamp=_utc_stamp(known_at or now())
    with connect() as db:
        rows=db.execute("SELECT * FROM chain_parties WHERE customer_id=? AND created_at<=? ORDER BY id,version",(customer_id,known_stamp)).fetchall()
    valid={}
    for row in rows:
        item=dict(row)
        if item["effective_from"]>valid_at: continue
        if item["effective_to"] and item["effective_to"]<=valid_at: continue
        prior=valid.get(item["id"])
        if not prior or item["version"]>prior["version"]: valid[item["id"]]=item
    return list(valid.values())

def chain_parties(customer_id=None,valid_at=None,known_at=None):
    if customer_id is not None:
        return _chain_rows(customer_id,valid_at,known_at)
    with connect() as db:
        rows=db.execute("SELECT c.* FROM chain_parties c JOIN (SELECT id,customer_id,MAX(version) version FROM chain_parties GROUP BY id,customer_id) latest ON c.id=latest.id AND c.customer_id=latest.customer_id AND c.version=latest.version ORDER BY c.created_at DESC").fetchall()
    return [dict(r) for r in rows]

def _chain_ancestors(party,by_id,depth=0):
    chain=[]; seen={party["id"]}; cur=party
    while cur.get("parent_party_id"):
        parent=by_id.get(cur["parent_party_id"])
        if parent is None or parent["id"] in seen: break
        seen.add(parent["id"]); chain.append({**parent,"depth":depth+1})
        cur=parent; depth+=1
    return chain

def _chain_descendants(party,by_id,depth=0):
    chain=[]; frontier=[party]; seen={party["id"]}
    while frontier:
        nxt=[]
        for node in frontier:
            for other in by_id.values():
                if other["id"] not in seen and other.get("parent_party_id")==node["id"]:
                    seen.add(other["id"]); nxt.append(other)
                    chain.append({**other,"depth":depth+1})
        frontier=nxt; depth+=1
    return chain

def chain_trace(customer_id,party_id,valid_at=None,known_at=None):
    rows=_chain_rows(customer_id,valid_at,known_at)
    by_id={r["id"]:r for r in rows}
    if party_id not in by_id: raise ValueError("Ketenpartij niet gevonden voor deze klant")
    party=by_id[party_id]
    return {"customer_id":customer_id,"party":party,
            "upstream":_chain_ancestors(party,by_id)+[party],
            "downstream":_chain_descendants(party,by_id)}

def chain_impact(customer_id,party_id,valid_at=None,known_at=None,thresholds=None):
    """Ketenimpact van een schakelwijziging: upstream+downstream keten, geraakte
    mandaten via dienstkoppeling op het activiteitenregister, thresholdovertredingen
    en open meldingstaken. Thresholds zijn parameters met bronverwijzing."""
    trace=chain_trace(customer_id,party_id,valid_at=valid_at,known_at=known_at)
    parties=[p for p in ([trace["party"]]+trace["downstream"])]
    threshold=dict(CHAIN_THRESHOLD_DEFAULTS)
    if thresholds:
        if not isinstance(thresholds,dict): raise ValueError("thresholds moet een object met source_ref zijn")
        if not thresholds.get("source_ref"): raise ValueError("thresholds vereisen een source_ref (policyparameter)")
        threshold.update(thresholds)
    breaches=[]
    if threshold.get("subcontract_share_pct") is not None:
        pct=float(threshold["subcontract_share_pct"])
        for p in parties:
            # partijfracties zijn 0-1; threshold is percentage — normaliseer naar %.
            if p.get("subcontract_share") is not None and float(p["subcontract_share"])*100>pct:
                breaches.append({"id":p["id"],"party_id":p["id"],"subcontract_share":p["subcontract_share"],"share_pct":round(float(p["subcontract_share"])*100,4),"threshold_pct":threshold["subcontract_share_pct"]})
    acts=activities(customer_id=customer_id,valid_at=valid_at,known_at=known_at)
    services={str(p["service"]).upper() for p in parties}
    affected=[a for a in acts if services & {str(s).upper() for s in (a.get("services") or [])}]
    with connect() as db:
        task_rows=db.execute("SELECT c.* FROM chain_tasks c JOIN (SELECT id,MAX(version) version FROM chain_tasks WHERE customer_id=? GROUP BY id) latest ON c.id=latest.id AND c.version=latest.version WHERE c.customer_id=? AND c.party_id=?",(customer_id,customer_id,party_id)).fetchall()
    open_tasks=[dict(t) for t in task_rows if t["status"]!="completed"]
    return {"customer_id":customer_id,"changed_party":trace["party"],
            "changed_party_and_downstream":[{"id":p["id"],"party_type":p["party_type"],"name":p["name"],"service":p["service"],"parent_party_id":p.get("parent_party_id")} for p in parties],
            "affected_mandates":[{"activity_id":a["id"],"activity_code":a["activity_code"],"fund_mandate_ref":a.get("fund_mandate_ref") or "",} for a in affected],
            "threshold_parameters":threshold,"threshold_breaches":breaches,
            "open_notification_tasks":open_tasks,
            "review_status":"pending",
            "validation_note":"te valideren door Compliance/Legal voor relevante klant/partij"}

def save_chain_party(data):
    required=(("customer_id"),"party_type","name","service","data_flow","jurisdiction","legal_entity","contract_ref","criticality","source_ref","rationale","effective_from")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["party_type"] not in CHAIN_PARTY_TYPES: raise ValueError("party_type moet direct, indirect of subcontractor zijn")
    if data["criticality"] not in ACTIVITY_CRITICALITY: raise ValueError("Kritikaliteit moet laag, gemiddeld of hoog zijn")
    share=data.get("subcontract_share")
    if share is not None:
        try: share=float(share)
        except (TypeError,ValueError): raise ValueError("subcontract_share moet een numerieke fractie zijn")
        if not 0<=share<=1: raise ValueError("subcontract_share moet tussen 0 en 1 liggen")
    pid=data.get("id") or "cty-"+re.sub(r"[^a-z0-9]+","-",str(data["name"]).lower()).strip("-")
    try:
        date.fromisoformat(str(data["effective_from"]))
    except ValueError: raise ValueError("Geldigheidsdatums moeten ISO-formaat YYYY-MM-DD hebben")
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM chain_parties WHERE id=? AND customer_id=?",(pid,data["customer_id"])).fetchone()["version"]
        parent=data.get("parent_party_id")
        if parent:
            prow=db.execute("SELECT * FROM chain_parties WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(parent,data["customer_id"])).fetchone()
            if prow is None: raise ValueError("Parentketenpartij niet gevonden voor deze klant")
            ancestors={prow["id"]}; cur=prow
            while cur["parent_party_id"]:
                nxt=db.execute("SELECT * FROM chain_parties WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(cur["parent_party_id"],data["customer_id"])).fetchone()
                if nxt is None or nxt["id"] in ancestors: break
                ancestors.add(nxt["id"]); cur=nxt
            if pid in ancestors: raise ValueError("Parentrelatie mag geen cyclus vormen")
        version=(previous or 0)+1
        stamp=now(); actor=data.get("actor","demo.client-service").strip()
        db.execute("INSERT INTO chain_parties VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(pid,version,data["customer_id"],data["party_type"],str(data["name"]).strip(),str(data["service"]).strip(),str(data["data_flow"]).strip(),str(data["jurisdiction"]).strip(),str(data["legal_entity"]).strip(),str(data["contract_ref"]).strip(),parent,data["criticality"],share,str(data["source_ref"]).strip(),str(data["effective_from"]).strip(),data.get("effective_to") or None,data["rationale"].strip(),actor,stamp))
        audit(db,"chain_parties",pid,"created" if version==1 else "versioned",actor,data["rationale"],{"customer_id":data["customer_id"],"version":version,"party_type":data["party_type"],"service":data["service"],"parent_party_id":parent,"criticality":data["criticality"],"subcontract_share":share,"source_ref":data["source_ref"]})
    with connect() as db: saved=db.execute("SELECT * FROM chain_parties WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,data["customer_id"])).fetchone()
    return dict(saved)

def chain_tasks(customer_id,party_id=None,known_at=None):
    known_stamp=_utc_stamp(known_at or now())
    with connect() as db:
        rows=db.execute("SELECT * FROM chain_tasks WHERE customer_id=? AND created_at<=?",(customer_id,known_stamp)).fetchall()
    grouped={}
    for row in rows:
        item=dict(row)
        prior=grouped.get(item["id"])
        if not prior or item["version"]>prior["version"]: grouped[item["id"]]=item
    return [t for t in grouped.values() if party_id is None or t["party_id"]==party_id]

def save_chain_task(data):
    required=(("customer_id"),"party_id","task_type","owner","deadline","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",str(data["deadline"])): raise ValueError("deadline moet ISO-formaat YYYY-MM-DD hebben")
    try: date.fromisoformat(str(data["deadline"]))
    except ValueError: raise ValueError("deadline moet ISO-formaat YYYY-MM-DD hebben")
    with connect() as db:
        prow=db.execute("SELECT 1 FROM chain_parties WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(data["party_id"],data["customer_id"])).fetchone()
        if prow is None: raise ValueError("Ketenpartij niet gevonden voor deze klant")
        tid=data.get("id") or "ctk-"+re.sub(r"[^a-z0-9]+","-",f"{data['customer_id']}-{data['party_id']}-{data['task_type']}".lower()).strip("-")
        status="completed" if data.get("status")=="completed" else "open"
        if status=="completed" and not data.get("completion_evidence"): raise ValueError("Afronding vereist bewijs (completion_evidence)")
        previous=db.execute("SELECT MAX(version) version FROM chain_tasks WHERE id=? AND customer_id=?",(tid,data["customer_id"])).fetchone()["version"]
        version=(previous or 0)+1
        stamp=now(); actor=data.get("actor","demo.compliance").strip()
        db.execute("INSERT INTO chain_tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(tid,version,data["customer_id"],data["party_id"],str(data["task_type"]).strip(),str(data["owner"]).strip(),str(data["deadline"]).strip(),status,data.get("completion_evidence"),str(data.get("source_ref") or "SYNTHETIC-AUDIT-001"),data["rationale"].strip(),actor,stamp))
        audit(db,"chain_tasks",tid,"created" if version==1 else "versioned",actor,data["rationale"],{"customer_id":data["customer_id"],"version":version,"party_id":data["party_id"],"task_type":data["task_type"],"owner":data["owner"],"deadline":data["deadline"],"status":status,"completion_evidence":data.get("completion_evidence")})
    with connect() as db: saved=db.execute("SELECT * FROM chain_tasks WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(tid,data["customer_id"])).fetchone()
    return dict(saved)

def complete_chain_task(task_id,customer_id,evidence,actor=None):
    if not evidence or not str(evidence).strip(): raise ValueError("Afronding vereist bewijs: evidence is verplicht")
    with connect() as db:
        rows=db.execute("SELECT * FROM chain_tasks WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(task_id,customer_id)).fetchone()
        if rows is None: raise ValueError("Meldingtaak niet gevonden")
        task=dict(rows)
        if task["status"]=="completed": raise ValueError("Meldingtaak is al afgerond; append-only, registreer een nieuwe taak of herziening")
    new=dict(task); new.update({"status":"completed","completion_evidence":str(evidence).strip(),"rationale":f"Afronding: {task['rationale']}","actor":actor or task["created_by"]})
    return save_chain_task({k:v for k,v in new.items() if k!="version"})

CONTRACT_MINIMUM_FIELDS = ("liability","transfer_of_rights","subcontracting","info_exchange","monitoring","audit_rights","supervisor_access","evaluation","term","exit_continuity","detailed_costs")

def missing_contract_fields(data):
    return [f for f in CONTRACT_MINIMUM_FIELDS if not data.get(f)]

def contract_minimums(customer_id=None,contract_ref=None,known_at=None):
    known_stamp=_utc_stamp(known_at or now())
    with connect() as db:
        q="SELECT * FROM contract_minimums WHERE created_at<=?"
        params=[known_stamp]
        if customer_id:
            q+=" AND customer_id=?"; params.append(customer_id)
        if contract_ref:
            q+=" AND contract_ref=?"; params.append(contract_ref)
        rows=db.execute(q,params).fetchall()
    grouped={}
    for row in rows:
        item=dict(row)
        prior=grouped.get(item["id"])
        if not prior or item["version"]>prior["version"]: grouped[item["id"]]=item
    return list(grouped.values())

def save_contract_minimum(data):
    required=("customer_id","contract_ref","subject_type","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["subject_type"] not in ("contract","party","mandate","activity"): raise ValueError("subject_type moet contract, party, mandate of activity zijn")
    cid=data["customer_id"]
    mid=data.get("id") or "cm-"+re.sub(r"[^a-z0-9]+","-",str(data["contract_ref"]).lower()).strip("-")
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM contract_minimums WHERE id=? AND customer_id=?",(mid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        stamp=now(); actor=data.get("actor","demo.client-service").strip()
        db.execute("INSERT INTO contract_minimums VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (mid,version,cid,str(data["contract_ref"]).strip(),str(data["subject_type"]).strip(),data.get("subject_id"),
             data.get("liability"),data.get("transfer_of_rights"),data.get("subcontracting"),
             data.get("info_exchange"),data.get("monitoring"),data.get("audit_rights"),
             data.get("supervisor_access"),data.get("evaluation"),data.get("term"),
             data.get("exit_continuity"),data.get("detailed_costs"),
             str(data["source_ref"]).strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"contract_minimums",mid,"created" if version==1 else "versioned",actor,data["rationale"],
            {"customer_id":cid,"version":version,"contract_ref":data["contract_ref"],"subject_type":data["subject_type"],
             "missing":missing_contract_fields(data)})
    with connect() as db: saved=db.execute("SELECT * FROM contract_minimums WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(mid,cid)).fetchone()
    return dict(saved)

SELECTION_CRITERIA_FIELDS = ("license_certification","financial_solidity","continuity","risk_management","integrity")

def missing_selection_criteria(data):
    return [f for f in SELECTION_CRITERIA_FIELDS if not data.get(f)]

def selection_assessments(customer_id=None, fund_ref=None, known_at=None):
    known_stamp=_utc_stamp(known_at or now())
    with connect() as db:
        q="SELECT * FROM selection_assessments WHERE created_at<=?"
        params=[known_stamp]
        if customer_id:
            q+=" AND customer_id=?"; params.append(customer_id)
        if fund_ref:
            q+=" AND fund_ref=?"; params.append(fund_ref)
        rows=db.execute(q,params).fetchall()
    grouped={}
    for row in rows:
        item=dict(row)
        prior=grouped.get(item["id"])
        if not prior or item["version"]>prior["version"]: grouped[item["id"]]=item
    return list(grouped.values())

def save_selection_assessment(data):
    required=("customer_id","fund_ref","subject_type","source_ref","rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip(): raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    if data["subject_type"] not in ("fund","mandate","party"): raise ValueError("subject_type moet fund, mandate of party zijn")
    cid=data["customer_id"]
    mid=data.get("id") or "sa-"+re.sub(r"[^a-z0-9]+","-",str(data["fund_ref"]).lower()).strip("-")
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM selection_assessments WHERE id=? AND customer_id=?",(mid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        stamp=now(); actor=data.get("actor","demo.client-service").strip()
        db.execute("INSERT INTO selection_assessments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (mid,version,cid,str(data["fund_ref"]).strip(),str(data["subject_type"]).strip(),data.get("subject_id"),
             data.get("license_certification"),data.get("financial_solidity"),data.get("continuity"),
             data.get("risk_management"),data.get("integrity"),
             data.get("evidence_ref"),data.get("review_cycle"),data.get("next_review_at"),data.get("status"),
             str(data["source_ref"]).strip(),data["rationale"].strip(),actor,stamp))
        audit(db,"selection_assessments",mid,"created" if version==1 else "versioned",actor,data["rationale"].strip(),
            {"customer_id":cid,"version":version,"fund_ref":data["fund_ref"],"subject_type":data["subject_type"],
             "missing":missing_selection_criteria(data)})
    with connect() as db: saved=db.execute("SELECT * FROM selection_assessments WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(mid,cid)).fetchone()
    return dict(saved)


NOTIFICATION_TRIGGER_TYPES = ("onboarding", "scope_change", "subcontracting", "offboarding")
NOTIFICATION_STATUS_VALUES = ("pending", "notified", "not_required", "review_required")
NOTIFICATION_REVIEW_FIELDS = ("owner", "deadline", "evidence_ref")

def missing_notification_fields(data):
    missing = []
    if not data.get("owner"): missing.append("owner")
    if not data.get("deadline") and not data.get("notified_at"): missing.append("deadline")
    if not data.get("evidence_ref"): missing.append("evidence_ref")
    return missing

def notification_signals(customer_id=None, fund_ref=None, known_at=None):
    known_stamp = _utc_stamp(known_at or now())
    with connect() as db:
        q = "SELECT * FROM notification_signals WHERE created_at<=?"
        params = [known_stamp]
        if customer_id:
            q += " AND customer_id=?"; params.append(customer_id)
        if fund_ref:
            q += " AND fund_ref=?"; params.append(fund_ref)
        rows = db.execute(q, params).fetchall()
    grouped = {}
    for row in rows:
        item = dict(row)
        prior = grouped.get(item["id"])
        if not prior or item["version"] > prior["version"]:
            grouped[item["id"]] = item
    return list(grouped.values())

def save_notification_signal(data):
    required = ("customer_id", "fund_ref", "subject_type", "trigger_type", "status", "source_ref", "rationale")
    for key in required:
        if data.get(key) is None or not str(data[key]).strip():
            raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]):
        raise ValueError("Klant niet gevonden")
    if data["subject_type"] not in ("fund", "mandate", "party"):
        raise ValueError("subject_type moet fund, mandate of party zijn")
    if data["trigger_type"] not in NOTIFICATION_TRIGGER_TYPES:
        raise ValueError("trigger_type ongeldig")
    if data["status"] not in NOTIFICATION_STATUS_VALUES:
        raise ValueError("status ongeldig")
    cid = data["customer_id"]
    mid = data.get("id") or "ns-" + re.sub(r"[^a-z0-9]+", "-", str(data["fund_ref"]).lower()).strip("-")
    with connect() as db:
        previous = db.execute("SELECT MAX(version) version FROM notification_signals WHERE id=? AND customer_id=?", (mid, cid)).fetchone()["version"]
        version = (previous or 0) + 1
        stamp = now()
        actor = data.get("actor", "demo.client-service").strip()
        db.execute("INSERT INTO notification_signals VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (mid, version, cid, str(data["fund_ref"]).strip(), str(data["subject_type"]).strip(), data.get("subject_id"),
             str(data["trigger_type"]).strip(), str(data["status"]).strip(),
             data.get("notified_at"), data.get("owner"), data.get("reference"),
             data.get("evidence_ref"), str(data["source_ref"]).strip(), data["rationale"].strip(),
             actor, stamp))
        audit(db, "notification_signals", mid, "created" if version == 1 else "versioned", actor, data["rationale"].strip(),
            {"customer_id": cid, "version": version, "fund_ref": data["fund_ref"],
             "trigger_type": data["trigger_type"], "status": data["status"],
             "missing": missing_notification_fields(data)})
    with connect() as db:
        saved = db.execute("SELECT * FROM notification_signals WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1", (mid, cid)).fetchone()
    return dict(saved)


CHANGE_AS_CODE_REQUIRED = ("customer_id", "entity_type", "entity_ref", "base_version", "effective_from", "diff", "rationale", "evidence_ref", "schema_version", "policy_version", "source_ref")

def save_change_as_code(data):
    for key in CHANGE_AS_CODE_REQUIRED:
        if data.get(key) is None or not str(data[key]).strip():
            raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]):
        raise ValueError("Klant niet gevonden")
    slug = "-".join((re.sub(r"[^a-z0-9]+", "-", s).strip("-") for s in (str(data["customer_id"]), str(data["entity_type"]), str(data["entity_ref"]), str(data["base_version"]))))
    pid = data.get("id") or f"change-{slug}"
    actor = data.get("actor", "demo.client-service")
    actor = actor.strip() if str(actor).strip() else "demo.client-service"
    stamp = now()
    cid = data["customer_id"]
    with connect() as db:
        previous = db.execute("SELECT MAX(version) version FROM change_as_code WHERE id=? AND customer_id=?", (pid, cid)).fetchone()["version"]
        version = (previous or 0) + 1
        db.execute("""INSERT INTO change_as_code(id,version,customer_id,entity_type,entity_ref,base_version,effective_from,diff,rationale,evidence_ref,schema_version,policy_version,source_ref,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pid, version, cid, data["entity_type"].strip(), data["entity_ref"].strip(), data["base_version"].strip(), data["effective_from"].strip(), str(data["diff"]).strip(), data["rationale"].strip(), data["evidence_ref"].strip(), data["schema_version"].strip(), data["policy_version"].strip(), data["source_ref"].strip(), actor, stamp))
        audit(db, "change_as_code", pid, "created" if version == 1 else "versioned", actor, data["rationale"].strip(), {"customer_id": cid, "version": version, "entity_type": data["entity_type"]})
    with connect() as db:
        saved = db.execute("SELECT * FROM change_as_code WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1", (pid, cid)).fetchone()
    return dict(saved)

def change_as_code(customer_id=None, entity_type=None, entity_ref=None):
    with connect() as db:
        q = "SELECT * FROM change_as_code WHERE 1=1"; params = []
        if customer_id: q += " AND customer_id=?"; params.append(customer_id)
        if entity_type: q += " AND entity_type=?"; params.append(entity_type)
        if entity_ref: q += " AND entity_ref=?"; params.append(entity_ref)
        rows = db.execute(q + " ORDER BY created_at DESC", params).fetchall()
    return [dict(r) for r in rows]

def change_as_code_export(customer_id=None, entity_type=None, entity_ref=None):
    rows = change_as_code(customer_id=customer_id, entity_type=entity_type, entity_ref=entity_ref)
    return {"generated_at": now(), "perimeter": {"customer_id": customer_id, "entity_type": entity_type, "entity_ref": entity_ref}, "coverage": len(rows), "rows": rows}

# aliases
save_change_as_codes = save_change_as_code
change_as_codes = change_as_code
change_as_codes_export = change_as_code_export

# TWIN-003 Impactanalyse
import json as _json2

IMPACT_ANALYSIS_REQUIRED = ("customer_id","baseline_ref","scenario_ref","domains","comparison","calc_logic_version","policy_version","schema_version","source_ref")

def save_impact_analysis(data):
    for key in IMPACT_ANALYSIS_REQUIRED:
        if data.get(key) is None or (isinstance(data[key],str) and not data[key].strip()):
            raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    slug="-".join((re.sub(r"[^a-z0-9]+","-",str(s).lower()).strip("-") for s in (data["customer_id"],data["baseline_ref"],data["scenario_ref"])))
    pid=data.get("id") or f"impact-{slug}"
    actor=data.get("actor","demo.client-service")
    if not str(actor).strip(): actor="demo.client-service"
    actor=str(actor).strip()
    stamp=now(); cid=data["customer_id"]
    domains=data["domains"]; comparison=data["comparison"]
    if not isinstance(domains,(dict,list,str)): raise ValueError("domains ongeldig")
    if not isinstance(comparison,(dict,list,str)): raise ValueError("comparison ongeldig")
    domains_json=domains if isinstance(domains,str) else _json2.dumps(domains,sort_keys=True)
    comparison_json=comparison if isinstance(comparison,str) else _json2.dumps(comparison,sort_keys=True)
    outcome=_json2.dumps({"domains":domains_json,"comparison":comparison_json,
        "calc_logic_version":data["calc_logic_version"],"policy_version":data["policy_version"],
        "schema_version":data["schema_version"]},sort_keys=True)
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM impact_analysis WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO impact_analysis(id,version,customer_id,baseline_ref,scenario_ref,domains,comparison,calc_logic_version,policy_version,schema_version,source_ref,valid_at,known_at,outcome,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,str(data["baseline_ref"]).strip(),str(data["scenario_ref"]).strip(),domains_json,comparison_json,
           str(data["calc_logic_version"]).strip(),str(data["policy_version"]).strip(),str(data["schema_version"]).strip(),str(data["source_ref"]).strip(),
           data.get("valid_at"),data.get("known_at"),outcome,actor,stamp))
        audit(db,"impact_analysis",pid,"created" if version==1 else "versioned",actor,"impact analysis",{"customer_id":cid,"version":version})
    with connect() as db: saved=db.execute("SELECT * FROM impact_analysis WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def impact_analyses(customer_id=None, baseline_ref=None, scenario_ref=None):
    with connect() as db:
        q="SELECT * FROM impact_analysis WHERE 1=1"; params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if baseline_ref: q+=" AND baseline_ref=?"; params.append(baseline_ref)
        if scenario_ref: q+=" AND scenario_ref=?"; params.append(scenario_ref)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def impact_analysis_export(customer_id=None, baseline_ref=None, scenario_ref=None):
    rows=impact_analyses(customer_id=customer_id,baseline_ref=baseline_ref,scenario_ref=scenario_ref)
    return {"generated_at":now(),"perimeter":{"customer_id":customer_id,"baseline_ref":baseline_ref,"scenario_ref":scenario_ref},"coverage":len(rows),"rows":rows}

# aliases
save_impact_analyses=save_impact_analysis
impact_analysis=impact_analyses
impact_analysis_export=impact_analysis_export

# EXP-001 Partnerprofielen (versioned mapping, validation, privacy filter, contract tests)
PARTNER_PROFILE_REQUIRED = ("customer_id","partner_id","partner_name","format","mapping","validation","classification","privacy_filter","schema_version","source_ref")

def save_partner_profile(data):
    for key in PARTNER_PROFILE_REQUIRED:
        if data.get(key) is None or (isinstance(data[key],str) and not data[key].strip()):
            raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    pid=data.get("id") or f"partner-{data['partner_id']}"
    actor=data.get("actor","demo.client-service")
    if not str(actor).strip(): actor="demo.client-service"
    actor=str(actor).strip()
    stamp=now(); cid=data["customer_id"]
    import json as _jp
    mapping=data["mapping"]; validation=data["validation"]; contract=data.get("contract_test",{})
    if not isinstance(mapping,(dict,list,str)): raise ValueError("mapping ongeldig")
    if not isinstance(validation,(dict,list,str)): raise ValueError("validation ongeldig")
    mapping_json=mapping if isinstance(mapping,str) else _jp.dumps(mapping,sort_keys=True)
    validation_json=validation if isinstance(validation,str) else _jp.dumps(validation,sort_keys=True)
    contract_json=contract if isinstance(contract,str) else _jp.dumps(contract,sort_keys=True)
    outcome=_jp.dumps({"mapping":mapping_json,"validation":validation_json,"classification":data["classification"],"privacy_filter":data["privacy_filter"],"schema_version":data["schema_version"]},sort_keys=True)
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM partner_profiles_versions WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO partner_profiles_versions(id,version,customer_id,partner_id,partner_name,format,mapping,validation,classification,privacy_filter,schema_version,contract_test,source_ref,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,str(data["partner_id"]).strip(),str(data["partner_name"]).strip(),str(data["format"]).strip(),mapping_json,validation_json,
           str(data["classification"]).strip(),str(data["privacy_filter"]).strip(),str(data["schema_version"]).strip(),contract_json,str(data["source_ref"]).strip(),actor,stamp))
        audit(db,"partner_profiles",pid,"created" if version==1 else "versioned",actor,"partner profile",{"customer_id":cid,"version":version})
    with connect() as db: saved=db.execute("SELECT * FROM partner_profiles_versions WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def partner_profiles(customer_id=None, partner_id=None, format=None):
    with connect() as db:
        q="SELECT * FROM partner_profiles_versions WHERE 1=1"; params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if partner_id: q+=" AND partner_id=?"; params.append(partner_id)
        if format: q+=" AND format=?"; params.append(format)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def partner_profile_export(customer_id=None, partner_id=None, format=None):
    rows=partner_profiles(customer_id=customer_id,partner_id=partner_id,format=format)
    return {"generated_at":now(),"perimeter":{"customer_id":customer_id,"partner_id":partner_id,"format":format},"coverage":len(rows),"rows":rows}

save_partner_profiles=save_partner_profile
partner_profile=partner_profiles
partner_profile_export=partner_profile_export
PUBLICATION_STATUS_REQUIRED = ("customer_id","export_id","checksum","snapshot_version","schema_version","mapping_version","actor","published_at","target","receipt_status","processing_status","source_ref")

def save_publication_status(data):
    for key in PUBLICATION_STATUS_REQUIRED:
        if data.get(key) is None or (isinstance(data[key],str) and not data[key].strip()):
            raise ValueError(f"{key} is verplicht")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    pid=data.get("id") or f"pub-{data['export_id']}"
    actor=str(data.get("actor","demo.client-service")).strip() or "demo.client-service"
    stamp=now(); cid=data["customer_id"]
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM publication_status_versions WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO publication_status_versions(id,version,customer_id,export_id,checksum,snapshot_version,schema_version,mapping_version,actor,published_at,target,receipt_status,processing_status,source_ref,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,str(data["export_id"]).strip(),str(data["checksum"]).strip(),str(data["snapshot_version"]).strip(),
           str(data["schema_version"]).strip(),str(data["mapping_version"]).strip(),actor,str(data["published_at"]).strip(),
           str(data["target"]).strip(),str(data["receipt_status"]).strip(),str(data["processing_status"]).strip(),
           str(data["source_ref"]).strip(),actor,stamp))
        audit(db,"publication_status",pid,"created" if version==1 else "versioned",actor,"publication status",{"customer_id":cid,"version":version,"export_id":data["export_id"]})
    with connect() as db: saved=db.execute("SELECT * FROM publication_status_versions WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def publication_statuses(customer_id=None, export_id=None, target=None, receipt_status=None):
    with connect() as db:
        q="SELECT * FROM publication_status_versions WHERE 1=1"; params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if export_id: q+=" AND export_id=?"; params.append(export_id)
        if target: q+=" AND target=?"; params.append(target)
        if receipt_status: q+=" AND receipt_status=?"; params.append(receipt_status)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def publication_status_export(customer_id=None, export_id=None, target=None):
    rows=publication_statuses(customer_id=customer_id,export_id=export_id,target=target)
    return {"generated_at":now(),"perimeter":{"customer_id":customer_id,"export_id":export_id,"target":target},"coverage":len(rows),"rows":rows}

save_publication_status=save_publication_status
publication_status=publication_statuses
publication_status_export=publication_status_export

INTEGRATION_REQUIRED = ("customer_id","source","direction","frequency","data_owner","contract","privacy_classification","reconciliation","actor","source_ref")
METHOD_PROFILE_REQUIRED = ("customer_id","mandate","method","cashflow_timing","actor","source_ref")

def save_integration(data):
    for key in INTEGRATION_REQUIRED:
        if data.get(key) is None or (isinstance(data[key],str) and not data[key].strip()):
            raise ValueError(f"{key} is verplicht")
    if data["direction"] not in {"inbound","outbound","bidirectional"}:
        raise ValueError("direction ongeldig")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    pid=data.get("id") or f"int-{data['source'].strip().lower().replace(' ','-')}"
    actor=str(data.get("actor","demo.client-service")).strip() or "demo.client-service"
    stamp=now(); cid=data["customer_id"]
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM integration_versions WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        db.execute("""INSERT INTO integration_versions(id,version,customer_id,source,direction,frequency,data_owner,contract,privacy_classification,reconciliation,endpoint,actor,source_ref,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (pid,version,cid,str(data["source"]).strip(),str(data["direction"]).strip(),str(data["frequency"]).strip(),
           str(data["data_owner"]).strip(),str(data["contract"]).strip(),str(data["privacy_classification"]).strip(),
           str(data["reconciliation"]).strip(),(data.get("endpoint") or None),actor,str(data["source_ref"]).strip(),actor,stamp))
        audit(db,"integration",pid,"created" if version==1 else "versioned",actor,"integration",{"customer_id":cid,"version":version,"source":data["source"]})
    with connect() as db: saved=db.execute("SELECT * FROM integration_versions WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def integrations(customer_id=None, source=None, direction=None):
    with connect() as db:
        q="SELECT * FROM integration_versions WHERE 1=1"; params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if source: q+=" AND source=?"; params.append(source)
        if direction: q+=" AND direction=?"; params.append(direction)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def integration_export(customer_id=None, source=None):
    rows=integrations(customer_id=customer_id,source=source)
    return {"generated_at":now(),"perimeter":{"customer_id":customer_id,"source":source},"coverage":len(rows),"rows":rows}

def record_integration_delivery(data):
    for key in ("customer_id","integration_id","payload_checksum","delivery_status","actor","source_ref"):
        if data.get(key) is None or (isinstance(data[key],str) and not data[key].strip()):
            raise ValueError(f"{key} is verplicht")
    if data["delivery_status"] not in {"delivered","failed","duplicate"}:
        raise ValueError("delivery_status ongeldig")
    if not customer(data["customer_id"]): raise ValueError("Klant niet gevonden")
    stamp=now()
    with connect() as db:
        db.execute("INSERT INTO integration_deliveries(integration_id,customer_id,payload_checksum,delivery_status,actor,source_ref,created_at) VALUES(?,?,?,?,?,?,?)",
          (str(data["integration_id"]).strip(),data["customer_id"],str(data["payload_checksum"]).strip(),str(data["delivery_status"]).strip(),str(data["actor"]).strip(),str(data["source_ref"]).strip(),stamp))
        audit(db,"integration_delivery",str(data["integration_id"]).strip(),"recorded",str(data["actor"]).strip(),"integration delivery",{"customer_id":data["customer_id"],"status":data["delivery_status"],"checksum":data["payload_checksum"]})
    with connect() as db: saved=db.execute("SELECT * FROM integration_deliveries WHERE customer_id=? AND integration_id=? ORDER BY id DESC LIMIT 1",(data["customer_id"],str(data["integration_id"]).strip())).fetchone()
    return dict(saved)

def integration_deliveries(customer_id=None, integration_id=None, delivery_status=None):
    with connect() as db:
        q="SELECT * FROM integration_deliveries WHERE 1=1"; params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if integration_id: q+=" AND integration_id=?"; params.append(integration_id)
        if delivery_status: q+=" AND delivery_status=?"; params.append(delivery_status)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

save_integration=save_integration
integration=integrations
METHOD_PROFILE_REQUIRED=["customer_id","mandate","method","cashflow_timing","actor","source_ref"]
METHODS_ALLOWED={"TWR","ModifiedDietz","IRR","MWR"}
CASHFLOW_TIMINGS={"BOD","EOD"}

def save_method_profile(data):
    for key in METHOD_PROFILE_REQUIRED:
        if data.get(key) is None or str(data.get(key)).strip()=="": raise ValueError(f"missing {key}")
    cid=data["customer_id"]
    with connect() as db:
        if not db.execute("SELECT 1 FROM customers WHERE id=?",(cid,)).fetchone():
            raise ValueError("unknown customer")
    mt=str(data["method"]).strip()
    ct=str(data["cashflow_timing"]).strip()
    if mt not in METHODS_ALLOWED: raise ValueError("invalid method")
    if ct not in CASHFLOW_TIMINGS: raise ValueError("invalid cashflow_timing")
    pid=str(data.get("id") or data.get("mandate")).strip() or str(data["mandate"]).strip()
    # id per mandate
    pid="method:"+str(data["mandate"]).strip()+":"+str(cid)
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM method_profile_versions WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        stamp=now()
        db.execute("""INSERT INTO method_profile_versions(id,version,customer_id,mandate,method,cashflow_timing,geometric_linking,gross_net_definition,fee_accrual,valuation_basis,price_source_timing,base_currency,reporting_currency,fx_source,fx_fixing,return_scope,derivatives_overlay_convention,reporting_periods,annualisation,inception_date,actor,source_ref,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pid,version,cid,str(data["mandate"]).strip(),mt,ct,
             1 if data.get("geometric_linking",True) else 0,
             (data.get("gross_net_definition") or "").strip() or None,
             (data.get("fee_accrual") or "").strip() or None,
             (data.get("valuation_basis") or "").strip() or None,
             (data.get("price_source_timing") or "").strip() or None,
             (data.get("base_currency") or "").strip() or None,
             (data.get("reporting_currency") or "").strip() or None,
             (data.get("fx_source") or "").strip() or None,
             (data.get("fx_fixing") or "").strip() or None,
             (data.get("return_scope") or "").strip() or None,
             (data.get("derivatives_overlay_convention") or "").strip() or None,
             (data.get("reporting_periods") or "").strip() or None,
             (data.get("annualisation") or "").strip() or None,
             (data.get("inception_date") or "").strip() or None,
             str(data["actor"]).strip(),str(data["source_ref"]).strip(),data.get("created_by"),stamp))
        audit(db,"method_profile",pid,"created" if version==1 else "versioned",str(data["actor"]).strip(),"method profile",{"customer_id":cid,"version":version,"mandate":data["mandate"],"method":mt})
    with connect() as db: saved=db.execute("SELECT * FROM method_profile_versions WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def method_profiles(customer_id=None, mandate=None, method=None):
    with connect() as db:
        q="SELECT * FROM method_profile_versions WHERE 1=1"; params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if mandate: q+=" AND mandate=?"; params.append(mandate)
        if method: q+=" AND method=?"; params.append(method)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def method_profile_export(customer_id=None, mandate=None):
    rows=method_profiles(customer_id=customer_id,mandate=mandate)
    return [{"id":r["id"],"version":r["version"],"mandate":r["mandate"],"method":r["method"],"cashflow_timing":r["cashflow_timing"],"created_at":r["created_at"]} for r in rows]

PENSION_PORTFOLIO_REQUIRED=["customer_id","mandate","portfolio_type","actor","source_ref"]
PORTFOLIO_TYPES={"return","matching","LDI"}

def save_pension_portfolio(data):
    for key in PENSION_PORTFOLIO_REQUIRED:
        if data.get(key) is None or str(data.get(key)).strip()=="": raise ValueError(f"missing {key}")
    cid=data["customer_id"]
    with connect() as db:
        if not db.execute("SELECT 1 FROM customers WHERE id=?",(cid,)).fetchone():
            raise ValueError("unknown customer")
    pt=str(data["portfolio_type"]).strip()
    if pt not in PORTFOLIO_TYPES: raise ValueError("invalid portfolio_type")
    pid="portfolio:"+str(data["mandate"]).strip()+":"+pt+":"+str(cid)
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM pension_portfolio_versions WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        stamp=now()
        db.execute("""INSERT INTO pension_portfolio_versions(id,version,customer_id,mandate,portfolio_type,swaps_overlay,hedge_return_vs_underlying,liabilities_benchmark,term_structure,coverage_ratio_indicator,hedge_ratio_indicator,actor,source_ref,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pid,version,cid,str(data["mandate"]).strip(),pt,
             (data.get("swaps_overlay") or "").strip() or None,
             (data.get("hedge_return_vs_underlying") or "").strip() or None,
             (data.get("liabilities_benchmark") or "").strip() or None,
             (data.get("term_structure") or "").strip() or None,
             (data.get("coverage_ratio_indicator") or "").strip() or None,
             (data.get("hedge_ratio_indicator") or "").strip() or None,
             str(data["actor"]).strip(),str(data["source_ref"]).strip(),data.get("created_by"),stamp))
        audit(db,"pension_portfolio",pid,"created" if version==1 else "versioned",str(data["actor"]).strip(),"pension portfolio",{"customer_id":cid,"version":version,"mandate":data["mandate"],"portfolio_type":pt})
    with connect() as db: saved=db.execute("SELECT * FROM pension_portfolio_versions WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def pension_portfolios(customer_id=None, mandate=None, portfolio_type=None):
    with connect() as db:
        q="SELECT * FROM pension_portfolio_versions WHERE 1=1"; params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if mandate: q+=" AND mandate=?"; params.append(mandate)
        if portfolio_type: q+=" AND portfolio_type=?"; params.append(portfolio_type)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def pension_portfolio_export(customer_id=None, mandate=None):
    rows=pension_portfolios(customer_id=customer_id,mandate=mandate)
    return [{"id":r["id"],"version":r["version"],"mandate":r["mandate"],"portfolio_type":r["portfolio_type"],"coverage_ratio_indicator":r["coverage_ratio_indicator"],"hedge_ratio_indicator":r["hedge_ratio_indicator"],"created_at":r["created_at"]} for r in rows]

integration_export=integration_export
BENCHMARK_REQUIRED=["customer_id","return_type","actor","source_ref","effective_date","history_policy"]
HISTORY_POLICIES={"revise","link"}
RETURN_TYPES={"total","net","price"}
REBALANCE_FREQUENCIES={"daily","monthly","quarterly","buy-and-hold"}

import json as _json

def save_benchmark(data):
    for key in BENCHMARK_REQUIRED:
        if data.get(key) is None or str(data.get(key)).strip()=="": raise ValueError(f"missing {key}")
    cid=data["customer_id"]
    with connect() as db:
        if not db.execute("SELECT 1 FROM customers WHERE id=?",(cid,)).fetchone():
            raise ValueError("unknown customer")
    rt=str(data["return_type"]).strip()
    if rt not in RETURN_TYPES: raise ValueError("invalid return_type")
    rf=data.get("rebalance_frequency")
    if rf is not None and str(rf).strip()!="" and str(rf).strip() not in REBALANCE_FREQUENCIES:
        raise ValueError("invalid rebalance_frequency")
    raw_name=data.get("name") or data.get("index_id") or "benchmark"
    name=raw_name.strip() if isinstance(raw_name,str) else str(raw_name)
    pid="benchmark:"+name+":"+str(cid)
    components=data.get("components")
    weights=data.get("weights")
    comp_text=_json.dumps(components) if not isinstance(components,str) and components is not None else (components or None)
    weight_text=_json.dumps(weights) if not isinstance(weights,str) and weights is not None else (weights or None)
    with connect() as db:
        previous=db.execute("SELECT MAX(version) version FROM benchmark_versions WHERE id=? AND customer_id=?",(pid,cid)).fetchone()["version"]
        version=(previous or 0)+1
        stamp=now()
        hp=data.get("history_policy")
        if hp is None or (isinstance(hp,str) and hp.strip()==""):
            raise ValueError("missing history_policy")
        hp_str=str(hp).strip()
        if hp_str not in HISTORY_POLICIES:
            raise ValueError("invalid history_policy")
        hp_val=hp_str
        eff=data.get("effective_date")
        vf=data.get("valid_from")
        # alias/conflict validation
        eff_str=None
        if eff is not None and not (isinstance(eff,str) and eff.strip()==""):
            eff_str=str(eff).strip()
        vf_str=None
        if vf is not None and not (isinstance(vf,str) and vf.strip()==""):
            vf_str=str(vf).strip()
        if eff_str is not None and vf_str is not None and eff_str!=vf_str:
            raise ValueError("conflicting effective_date/valid_from")
        valid_time = eff_str if eff_str is not None else vf_str
        if valid_time is None:
            raise ValueError("missing effective_date")
        # validate calendar date / timestamp format
        import datetime as _dt
        for cand in (valid_time,):
            try:
                # accept date or ISO timestamp
                if "T" in cand:
                    _dt.datetime.fromisoformat(cand.replace("Z","+00:00"))
                else:
                    _dt.date.fromisoformat(cand)
            except ValueError:
                raise ValueError("invalid effective_date")
        eff_val=valid_time
        # authoritative valid_from
        data["valid_from"]=valid_time
        known=data.get("known_at")
        known_val=(known.strip() if isinstance(known,str) and known.strip()!="" else None) if known is not None else None
        if known_val is None:
            known_val=stamp
        db.execute("""INSERT INTO benchmark_versions(id,version,customer_id,name,benchmark_type,index_id,provider,return_type,currency,hedge_status,components,weights,rebalance_frequency,valid_from,valid_to,effective_date,history_policy,known_at,actor,source_ref,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pid,version,cid,name,
             (data.get("benchmark_type") or "").strip() or None,
             (data.get("index_id") or "").strip() or None if isinstance(data.get("index_id"),str) else data.get("index_id"),
             (data.get("provider") or "").strip() or None if isinstance(data.get("provider"),str) else data.get("provider"),
             rt,
             (data.get("currency") or "").strip() or None if isinstance(data.get("currency"),str) else data.get("currency"),
             (data.get("hedge_status") or "").strip() or None if isinstance(data.get("hedge_status"),str) else data.get("hedge_status"),
             comp_text, weight_text,
             (str(rf).strip() if rf is not None and str(rf).strip()!="" else None),
             (data.get("valid_from") or "").strip() or None if isinstance(data.get("valid_from"),str) else data.get("valid_from"),
             (data.get("valid_to") or "").strip() or None if isinstance(data.get("valid_to"),str) else data.get("valid_to"),
             eff_val, hp_val, known_val,
             str(data["actor"]).strip(),str(data["source_ref"]).strip(),data.get("created_by"),stamp))
        audit(db,"benchmark",pid,"created" if version==1 else "versioned",str(data["actor"]).strip(),"benchmark",{"customer_id":cid,"version":version,"return_type":rt})
    with connect() as db: saved=db.execute("SELECT * FROM benchmark_versions WHERE id=? AND customer_id=? ORDER BY version DESC LIMIT 1",(pid,cid)).fetchone()
    return dict(saved)

def benchmarks(customer_id=None, return_type=None, index_id=None):
    with connect() as db:
        q="SELECT * FROM benchmark_versions WHERE 1=1"; params=[]
        if customer_id: q+=" AND customer_id=?"; params.append(customer_id)
        if return_type: q+=" AND return_type=?"; params.append(return_type)
        if index_id: q+=" AND index_id=?"; params.append(index_id)
        rows=db.execute(q+" ORDER BY created_at DESC",params).fetchall()
    return [dict(r) for r in rows]

def benchmarks_as_of(customer_id=None, valid_at=None, known_at=None, return_type=None, index_id=None):
    """Return benchmark versions effective at valid_at and recorded by known_at (bitemporal read)."""
    known_stamp = _utc_stamp(known_at or now())
    with connect() as db:
        q = "SELECT * FROM benchmark_versions WHERE created_at<=?"; params=[known_stamp]
        if customer_id: q += " AND customer_id=?"; params.append(customer_id)
        if return_type: q += " AND return_type=?"; params.append(return_type)
        if index_id: q += " AND index_id=?"; params.append(index_id)
        rows = db.execute(q + " ORDER BY id,version", params).fetchall()
    grouped = {}
    for row in rows:
        item = dict(row)
        vf = item.get("valid_from") or item.get("effective_date")
        if valid_at is not None and vf is not None and vf > valid_at:
            continue
        if item.get("valid_to") is not None and valid_at is not None and item["valid_to"] <= valid_at:
            continue
        # history policy revise vs link: revise supersedes prior same id; link keeps both
        prior = grouped.get(item["id"])
        if prior is None:
            grouped[item["id"]] = item
        else:
            if (item.get("version") or 0) > (prior.get("version") or 0):
                if item.get("history_policy") == "revise":
                    grouped[item["id"]] = item
                else:
                    # link: keep both as separate entries
                    grouped.setdefault(item["id"] + "::" + str(item["version"]), item)
    # flatten
    result = []
    for k, v in grouped.items():
        v = dict(v)
        v["valid_at"] = valid_at
        v["known_at"] = known_stamp
        result.append(v)
    return sorted(result, key=lambda r: (r.get("id") or "", r.get("version") or 0))

def benchmark_export(customer_id=None):
    rows=benchmarks(customer_id=customer_id)
    return [{"id":r["id"],"version":r["version"],"index_id":r["index_id"],"provider":r["provider"],"return_type":r["return_type"],"currency":r["currency"],"hedge_status":r["hedge_status"],"rebalance_frequency":r["rebalance_frequency"],"valid_from":r["valid_from"],"valid_to":r["valid_to"],"effective_date":r["effective_date"],"history_policy":r["history_policy"],"known_at":r["known_at"],"created_at":r["created_at"]} for r in rows]

save_benchmark=save_benchmark
benchmark=benchmarks
benchmark_export=benchmark_export
benchmarks_as_of=benchmarks_as_of
benchmark_as_of=benchmarks_as_of
record_integration_delivery=record_integration_delivery
save_method_profile=save_method_profile
method_profile=method_profiles
method_profile_export=method_profile_export
save_pension_portfolio=save_pension_portfolio
pension_portfolio=pension_portfolios
pension_portfolio_export=pension_portfolio_export
integration_delivery=integration_deliveries
