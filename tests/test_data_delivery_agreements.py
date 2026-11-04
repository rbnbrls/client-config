import os, sys, tempfile, sqlite3, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="dda-")+ "/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",supplier_ref="fund-1",supplier_role="fund",field="PAI-Indicator-1",period="2025-Q1",channel="sftp",validation="schema+range",proof="hash-abc",source_ref="SYNTHETIC-SRC",rationale="dda")

class DDA(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()
    def test_save_basic(self):
        r=store.save_data_delivery_agreement(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["supplier_role"],"fund")
    def test_required(self):
        for key in ("customer_id","supplier_ref","supplier_role","field","period","channel","validation","proof","source_ref","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_data_delivery_agreement(d)
    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_data_delivery_agreement({**BASE,"customer_id":"unknown"})
    def test_role_enum(self):
        with self.assertRaises(ValueError):
            store.save_data_delivery_agreement({**BASE,"supplier_role":"nope"})
    def test_append_only(self):
        store.save_data_delivery_agreement(BASE)
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE data_delivery_agreements SET field='x'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM data_delivery_agreements WHERE customer_id=?",("northstar",))
    def test_versioned(self):
        store.save_data_delivery_agreement(BASE)
        store.save_data_delivery_agreement({**BASE,"validation":"revised"})
        with store.connect() as db:
            vers=[r["version"] for r in db.execute("SELECT version FROM data_delivery_agreements WHERE customer_id=?",("northstar",)).fetchall()]
        self.assertEqual(sorted(vers),[1,2])
    def test_query(self):
        store.save_data_delivery_agreement(BASE)
        res=store.data_delivery_agreements(customer_id="northstar",supplier_role="fund",field="PAI-Indicator-1")
        self.assertEqual(len(res),1)

if __name__=="__main__":
    unittest.main()