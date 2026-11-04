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
        dora_columns={r["name"] for r in db.execute("PRAGMA table_info(dora_assessments)")}
        if "effective_from" not in dora_columns: db.execute("ALTER TABLE dora_assessments ADD COLUMN effective_from TEXT")
        if "effective_to" not in dora_columns: db.execute("ALTER TABLE dora_assessments ADD COLUMN effective_to TEXT")
        config_columns={r["name"] for r in db.execute("PRAGMA table_info(config_versions)")}
        if "schema_version" not in config_columns: db.execute("ALTER TABLE config_versions ADD COLUMN schema_version TEXT NOT NULL DEFAULT '1'")
        change_columns={r["name"] for r in db.execute("PRAGMA table_info(change_sets)")}
        if "schema_version" not in change_columns: db.execute("ALTER TABLE change_sets ADD COLUMN schema_version TEXT NOT NULL DEFAULT '1'")
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
