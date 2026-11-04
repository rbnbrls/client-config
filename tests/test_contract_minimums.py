import os, sys, tempfile, sqlite3, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="cm-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",contract_ref="SYNTHETIC-CONTRACT-001",subject_type="contract",
    source_ref="SYNTHETIC-CONTRACT-001",rationale="minimumvelden registratie",actor="demo.client-service")

class CM(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()
    def test_save_basic(self):
        r=store.save_contract_minimum({**BASE})
        self.assertEqual(r["contract_ref"],"SYNTHETIC-CONTRACT-001")
        self.assertEqual(r["version"],1)
    def test_required_fields(self):
        for key in ("customer_id","contract_ref","subject_type","source_ref","rationale"):
            with self.assertRaises(ValueError):
                store.save_contract_minimum({**BASE,key:None})
    def test_missing_fields_list(self):
        m=store.missing_contract_fields({**BASE})
        self.assertIn("liability",m)
        self.assertEqual(len(m),len(store.CONTRACT_MINIMUM_FIELDS))
    def test_versioned_no_overwrite(self):
        store.save_contract_minimum({**BASE,"liability":"hoog"})
        store.save_contract_minimum({**BASE,"liability":"hoog","term":"5 jaar","rationale":"herziening"})
        with store.connect() as db:
            vers=[r["version"] for r in db.execute("SELECT version FROM contract_minimums WHERE customer_id=? AND contract_ref=?",("northstar","SYNTHETIC-CONTRACT-001")).fetchall()]
        self.assertEqual(sorted(vers),[1,2])
    def test_append_only_delete_blocked(self):
        store.save_contract_minimum({**BASE})
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM contract_minimums WHERE customer_id=? AND contract_ref=?",("northstar","SYNTHETIC-CONTRACT-001"))
    def test_missing_customer_rejected(self):
        with self.assertRaises(ValueError):
            store.save_contract_minimum({**BASE,"customer_id":"unknown"})
    def test_subject_type_enum(self):
        with self.assertRaises(ValueError):
            store.save_contract_minimum({**BASE,"subject_type":"onbekend"})
    def test_query_customer(self):
        store.save_contract_minimum({**BASE})
        res=store.contract_minimums(customer_id="northstar")
        self.assertEqual(len(res),1)

if __name__=="__main__":
    import unittest; unittest.main()
