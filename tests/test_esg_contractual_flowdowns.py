import os, sys, tempfile, sqlite3, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="esgfd-")+ "/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",fund_ref="SYNTHETIC-FUND-001",manager_ref="SYNTHETIC-MGR-001",
    clause="oecd_ungp",source_ref="SYNTHETIC-SRC",rationale="flowdown")

class ESG003(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()
    def test_save_basic(self):
        r=store.save_esg_contractual_flowdown(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["clause"],"oecd_ungp")
        self.assertEqual(r["target"],"direct_manager")
    def test_required(self):
        for key in ("customer_id","fund_ref","manager_ref","clause","source_ref","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_esg_contractual_flowdown(d)
    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_esg_contractual_flowdown({**BASE,"customer_id":"unknown"})
    def test_target_enum(self):
        with self.assertRaises(ValueError):
            store.save_esg_contractual_flowdown({**BASE,"target":"nope"})
    def test_clause_enum(self):
        with self.assertRaises(ValueError):
            store.save_esg_contractual_flowdown({**BASE,"clause":"nope"})
    def test_sub_manager_flowdown(self):
        r=store.save_esg_contractual_flowdown({**BASE,"target":"sub_manager","sub_manager_ref":"SYNTHETIC-SUB-001","clause":"escalation"})
        self.assertEqual(r["target"],"sub_manager")
        self.assertEqual(r["sub_manager_ref"],"SYNTHETIC-SUB-001")
    def test_exception_requires_approver_end_date(self):
        with self.assertRaises(ValueError):
            store.save_esg_contractual_flowdown({**BASE,"exception_rationale":"r"})
        with self.assertRaises(ValueError):
            store.save_esg_contractual_flowdown({**BASE,"exception_end_date":"2026-12-31"})
    def test_append_only(self):
        store.save_esg_contractual_flowdown(BASE)
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE esg_contractual_flowdowns SET clause='due_diligence'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM esg_contractual_flowdowns WHERE customer_id=?",("northstar",))
    def test_versioned(self):
        store.save_esg_contractual_flowdown(BASE)
        store.save_esg_contractual_flowdown({**BASE,"rationale":"herzien"})
        with store.connect() as db:
            vers=[r["version"] for r in db.execute("SELECT version FROM esg_contractual_flowdowns WHERE customer_id=? AND fund_ref=?",
                ("northstar","SYNTHETIC-FUND-001")).fetchall()]
        self.assertEqual(sorted(vers),[1,2])
    def test_validity_expired(self):
        store.save_esg_contractual_flowdown({**BASE,"exception_rationale":"uitzondering","exception_approver":"Compliance","exception_end_date":"2026-06-30"})
        rows=store.esg_contractual_flowdowns(customer_id="northstar",valid_at="2026-07-01")
        self.assertEqual(rows[0]["validity_status"],"expired")

if __name__=="__main__":
    unittest.main()
