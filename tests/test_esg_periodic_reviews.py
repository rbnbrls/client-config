import os, sys, tempfile, sqlite3, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="esgpr-")+ "/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",fund_ref="SYNTHETIC-FUND-001",manager_ref="SYNTHETIC-MGR-001",
    review_period="annual",esg_risks="ESG risk X",results="score 70",improvement_actions="actie",
    source_ref="SYNTHETIC-SRC",rationale="pr")

class ESG006(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()
    def test_save_basic(self):
        r=store.save_esg_periodic_review(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["deviation"],"none")
        self.assertEqual(r["escalation"],"none")
    def test_required(self):
        for key in ("customer_id","fund_ref","manager_ref","esg_risks","results","source_ref","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_esg_periodic_review(d)
    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_esg_periodic_review({**BASE,"customer_id":"unknown"})
    def test_period_enum(self):
        with self.assertRaises(ValueError):
            store.save_esg_periodic_review({**BASE,"review_period":"nope"})
    def test_deviation_enum(self):
        with self.assertRaises(ValueError):
            store.save_esg_periodic_review({**BASE,"deviation":"nope"})
    def test_escalation_enum(self):
        with self.assertRaises(ValueError):
            store.save_esg_periodic_review({**BASE,"escalation":"nope"})
    def test_deviation_requires_rationale_approver_enddate(self):
        for missing in ("deviation_rationale","approver","end_date"):
            d={**BASE,"deviation":"deferral","deviation_rationale":"r","approver":"a","end_date":"2026-12-31"}
            d[missing]=None
            with self.assertRaises(ValueError):
                store.save_esg_periodic_review(d)
    def test_append_only(self):
        store.save_esg_periodic_review(BASE)
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE esg_periodic_reviews SET results='x'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM esg_periodic_reviews WHERE customer_id=? ",("northstar",))
    def test_versioned(self):
        store.save_esg_periodic_review(BASE)
        store.save_esg_periodic_review({**BASE,"results":"herzien"})
        with store.connect() as db:
            vers=[r["version"] for r in db.execute("SELECT version FROM esg_periodic_reviews WHERE customer_id=? AND fund_ref=?",
                ("northstar","SYNTHETIC-FUND-001")).fetchall()]
        self.assertEqual(sorted(vers),[1,2])
    def test_query(self):
        store.save_esg_periodic_review(BASE)
        res=store.esg_periodic_reviews(customer_id="northstar",review_period="annual")
        self.assertEqual(len(res),1)

if __name__=="__main__":
    unittest.main()
