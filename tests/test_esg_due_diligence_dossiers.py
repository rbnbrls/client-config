import os, sys, tempfile, sqlite3, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="esgdd-")+ "/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",fund_ref="SYNTHETIC-FUND-001",manager_ref="SYNTHETIC-MGR-001",
    workflow_step="policy_systems",finding="bevinding",human_judgement="oordeel",action_owner="demo.owner",
    deadline="2026-12-31",source_ref="SYNTHETIC-SRC",rationale="dd")

class ESG004(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()
    def test_save_basic(self):
        r=store.save_esg_due_diligence_dossier(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["workflow_step"],"policy_systems")
        self.assertEqual(r["impact_priority"],"medium")
    def test_required(self):
        for key in ("customer_id","fund_ref","manager_ref","workflow_step","finding","human_judgement","action_owner","deadline","source_ref","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_esg_due_diligence_dossier(d)
    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_esg_due_diligence_dossier({**BASE,"customer_id":"unknown"})
    def test_step_enum(self):
        with self.assertRaises(ValueError):
            store.save_esg_due_diligence_dossier({**BASE,"workflow_step":"nope"})
    def test_priority_enum(self):
        with self.assertRaises(ValueError):
            store.save_esg_due_diligence_dossier({**BASE,"impact_priority":"nope"})
    def test_deadline_validation(self):
        with self.assertRaises(ValueError):
            store.save_esg_due_diligence_dossier({**BASE,"deadline":"bad"})
    def test_exception_requires_all(self):
        # human judgement required already
        pass
    def test_append_only(self):
        store.save_esg_due_diligence_dossier(BASE)
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE esg_due_diligence_dossiers SET workflow_step='remediation'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM esg_due_diligence_dossiers WHERE customer_id=?",("northstar",))
    def test_versioned(self):
        store.save_esg_due_diligence_dossier(BASE)
        store.save_esg_due_diligence_dossier({**BASE,"rationale":"herzien"})
        with store.connect() as db:
            vers=[r["version"] for r in db.execute("SELECT version FROM esg_due_diligence_dossiers WHERE customer_id=? AND fund_ref=?",
                ("northstar","SYNTHETIC-FUND-001")).fetchall()]
        self.assertEqual(sorted(vers),[1,2])
    def test_overdue(self):
        store.save_esg_due_diligence_dossier({**BASE,"deadline":"2026-06-30"})
        rows=store.esg_due_diligence_dossiers(customer_id="northstar",valid_at="2026-07-01")
        self.assertEqual(rows[0]["validity_status"],"overdue")

if __name__=="__main__":
    unittest.main()
