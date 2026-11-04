import os, sys, tempfile, sqlite3, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="sa-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",fund_ref="SYNTHETIC-FUND-001",subject_type="fund",
    source_ref="SYNTHETIC-SOURCE-001",rationale="selectiebeoordeling",actor="demo.client-service")

class SA(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()
    def test_save_basic(self):
        r=store.save_selection_assessment({**BASE})
        self.assertEqual(r["fund_ref"],"SYNTHETIC-FUND-001")
        self.assertEqual(r["version"],1)
    def test_required_fields(self):
        for key in ("customer_id","fund_ref","subject_type","source_ref","rationale"):
            with self.assertRaises(ValueError):
                store.save_selection_assessment({**BASE,key:None})
    def test_missing_criteria_list(self):
        m=store.missing_selection_criteria({**BASE})
        self.assertIn("license_certification",m)
        self.assertEqual(len(m),len(store.SELECTION_CRITERIA_FIELDS))
    def test_versioned_no_overwrite(self):
        store.save_selection_assessment({**BASE,"license_certification":"vergunning ok"})
        store.save_selection_assessment({**BASE,"license_certification":"vergunning ok","integrity":"schoon","rationale":"herziening"})
        with store.connect() as db:
            vers=[r["version"] for r in db.execute("SELECT version FROM selection_assessments WHERE customer_id=? AND fund_ref=?",("northstar","SYNTHETIC-FUND-001")).fetchall()]
        self.assertEqual(sorted(vers),[1,2])
    def test_append_only_delete_blocked(self):
        store.save_selection_assessment({**BASE})
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM selection_assessments WHERE customer_id=? AND fund_ref=?",("northstar","SYNTHETIC-FUND-001"))
    def test_missing_customer_rejected(self):
        with self.assertRaises(ValueError):
            store.save_selection_assessment({**BASE,"customer_id":"unknown"})
    def test_subject_type_enum(self):
        with self.assertRaises(ValueError):
            store.save_selection_assessment({**BASE,"subject_type":"onbekend"})
    def test_query_customer(self):
        store.save_selection_assessment({**BASE})
        res=store.selection_assessments(customer_id="northstar")
        self.assertEqual(len(res),1)

if __name__=="__main__":
    import unittest; unittest.main()