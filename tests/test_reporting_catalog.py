import os, sys, tempfile, sqlite3, json, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="rpt-")+ "/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",report_type="regulatory",data_item="PAI-Indicator-1",definition="def",unit="pct",
    perimeter="portfolio",calculation_source="system",frequency="annual",recipients=["compliance@example.test","client@example.test"],
    source_ref="SYNTHETIC-SRC",rationale="rpt")

class RPT001(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()
    def test_save_basic(self):
        r=store.save_reporting_catalog_item(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["report_type"],"regulatory")
        self.assertEqual(r["frequency"],"annual")
        self.assertEqual(r["language"],"nl")
        self.assertEqual(json.loads(r["recipients"]),BASE["recipients"])
    def test_required(self):
        for key in ("customer_id","report_type","data_item","definition","unit","perimeter","calculation_source","frequency","recipients","source_ref","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_reporting_catalog_item(d)
    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_reporting_catalog_item({**BASE,"customer_id":"unknown"})
    def test_report_type_enum(self):
        with self.assertRaises(ValueError):
            store.save_reporting_catalog_item({**BASE,"report_type":"nope"})
    def test_frequency_enum(self):
        with self.assertRaises(ValueError):
            store.save_reporting_catalog_item({**BASE,"frequency":"nope"})
    def test_language_enum(self):
        with self.assertRaises(ValueError):
            store.save_reporting_catalog_item({**BASE,"language":"xx"})
    def test_append_only(self):
        store.save_reporting_catalog_item(BASE)
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE reporting_catalog SET data_item='x'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM reporting_catalog WHERE customer_id=?",("northstar",))
    def test_versioned(self):
        store.save_reporting_catalog_item(BASE)
        store.save_reporting_catalog_item({**BASE,"definition":"herzien"})
        with store.connect() as db:
            vers=[r["version"] for r in db.execute("SELECT version FROM reporting_catalog WHERE customer_id=? AND report_type=?",
                ("northstar","regulatory")).fetchall()]
        self.assertEqual(sorted(vers),[1,2])
    def test_query(self):
        store.save_reporting_catalog_item(BASE)
        res=store.reporting_catalog_items(customer_id="northstar",report_type="regulatory",frequency="annual")
        self.assertEqual(len(res),1)
    def test_recipients_string(self):
        r=store.save_reporting_catalog_item({**BASE,"recipients":"a@b.test"})
        self.assertEqual(r["recipients"],"a@b.test")

if __name__=="__main__":
    unittest.main()
