import os, sys, tempfile, sqlite3, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="tr-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",disclosure_ref="DISC-2025-Q1",manager_ref="MGR-ACME",data_coverage="full",confidentiality_flag="confidential",publication_consent="pending",publication_scope="client-reporting",schema_version="1",methodology_version="1.0",source_ref="SYNTHETIC-SRC",rationale="ok")

class TR(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()
    def test_save_basic(self):
        r=store.save_transparency_output(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["confidentiality_flag"],"confidential")
    def test_required(self):
        for key in ("customer_id","disclosure_ref","source_ref","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_transparency_output(d)
    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_transparency_output({**BASE,"customer_id":"unknown"})
    def test_confidentiality_enum(self):
        with self.assertRaises(ValueError):
            store.save_transparency_output({**BASE,"confidentiality_flag":"nope"})
    def test_consent_enum(self):
        with self.assertRaises(ValueError):
            store.save_transparency_output({**BASE,"publication_consent":"nope"})
    def test_append_only(self):
        store.save_transparency_output(BASE)
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE transparency_outputs SET data_coverage='x'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM transparency_outputs WHERE customer_id=? ",("northstar",))
    def test_versioned(self):
        store.save_transparency_output(BASE)
        store.save_transparency_output({**BASE,"publication_consent":"granted"})
        with store.connect() as db:
            vers=[r["version"] for r in db.execute("SELECT version FROM transparency_outputs WHERE customer_id=? ",("northstar",)).fetchall()]
        self.assertEqual(sorted(vers),[1,2])
    def test_query(self):
        store.save_transparency_output(BASE)
        res=store.transparency_outputs(customer_id="northstar",disclosure_ref="DISC-2025-Q1",publication_consent="pending")
        self.assertEqual(len(res),1)

if __name__=="__main__":
    unittest.main()