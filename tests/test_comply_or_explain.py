import os, sys, tempfile, sqlite3, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="ce-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",code_ref="CSR-001",compliance_status="comply",deviation_explanation="n/a",validity_from="2025-01-01",validity_to="2025-12-31",impact="low",approver="compliance",follow_up_action="none",source_ref="SYNTHETIC-SRC",rationale="ok")

class CE(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()
    def test_save_basic(self):
        r=store.save_comply_or_explain(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["compliance_status"],"comply")
    def test_required(self):
        for key in ("customer_id","code_ref","compliance_status","deviation_explanation","validity_from","validity_to","impact","approver","follow_up_action","source_ref","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_comply_or_explain(d)
    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_comply_or_explain({**BASE,"customer_id":"unknown"})
    def test_status_enum(self):
        with self.assertRaises(ValueError):
            store.save_comply_or_explain({**BASE,"compliance_status":"nope"})
    def test_append_only(self):
        store.save_comply_or_explain(BASE)
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE comply_or_explain SET impact='x'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM comply_or_explain WHERE customer_id=? ",("northstar",))
    def test_versioned(self):
        store.save_comply_or_explain(BASE)
        store.save_comply_or_explain({**BASE,"impact":"high"})
        with store.connect() as db:
            vers=[r["version"] for r in db.execute("SELECT version FROM comply_or_explain WHERE customer_id=? ",("northstar",)).fetchall()]
        self.assertEqual(sorted(vers),[1,2])
    def test_query(self):
        store.save_comply_or_explain(BASE)
        res=store.comply_or_explain(customer_id="northstar",code_ref="CSR-001",compliance_status="comply")
        self.assertEqual(len(res),1)

if __name__=="__main__":
    unittest.main()