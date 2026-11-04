import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="mgrlt-")+ "/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",manager_ref="MGR-01",fund_ref="FUND-SYNTH-01",asset_class="equities",
    coverage_date="2026-03-31",disclosure_permission="permitted",source_ref="SYNTHETIC-SRC",rationale="ok")

class ManagerLookThrough(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()

    def test_save_basic(self):
        r=store.save_manager_look_through(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["disclosure_permission"],"permitted")

    def test_required(self):
        for key in ("customer_id","manager_ref","fund_ref","asset_class","coverage_date","disclosure_permission","source_ref","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_manager_look_through(d)

    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_manager_look_through({**BASE,"customer_id":"unknown"})

    def test_disclosure_enum(self):
        with self.assertRaises(ValueError):
            store.save_manager_look_through({**BASE,"disclosure_permission":"nope"})

    def test_append_only(self):
        store.save_manager_look_through(BASE)
        with store.connect() as db:
            with self.assertRaises(Exception):
                db.execute("UPDATE manager_look_through SET aum=999")
            with self.assertRaises(Exception):
                db.execute("DELETE FROM manager_look_through")

    def test_versioning(self):
        store.save_manager_look_through(BASE)
        r2=store.save_manager_look_through({**BASE,"aum":1000})
        self.assertEqual(r2["version"],2)

    def test_export(self):
        store.save_manager_look_through(BASE)
        ex=store.manager_look_through_export(customer_id="northstar")
        self.assertEqual(ex["coverage"],1)
        self.assertIn("perimeter",ex)
        self.assertIn("generated_at",ex)

    def test_list_filter(self):
        store.save_manager_look_through(BASE)
        store.save_manager_look_through({**BASE,"disclosure_permission":"restricted","coverage_date":"2026-06-30"})
        rows=store.manager_look_through(customer_id="northstar",disclosure_permission="restricted")
        self.assertEqual(len(rows),1)

if __name__=="__main__":
    unittest.main()