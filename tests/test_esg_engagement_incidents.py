import os, sys, tempfile, sqlite3, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="esgei-")+ "/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",fund_ref="SYNTHETIC-FUND-001",manager_ref="SYNTHETIC-MGR-001",
    incident="controverse X",source_ref="SYNTHETIC-SRC",severity="medium",
    engagement_relation="direct",engagement_goal="remediatie",rationale="ei")

class ESG005(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()
    def test_save_basic(self):
        r=store.save_esg_engagement_incident(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["progress"],"open")
        self.assertEqual(r["retention_decision"],"pending")
    def test_required(self):
        for key in ("customer_id","fund_ref","manager_ref","incident","source_ref","severity","engagement_relation","engagement_goal","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_esg_engagement_incident(d)
    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_esg_engagement_incident({**BASE,"customer_id":"unknown"})
    def test_severity_enum(self):
        with self.assertRaises(ValueError):
            store.save_esg_engagement_incident({**BASE,"severity":"nope"})
    def test_progress_enum(self):
        with self.assertRaises(ValueError):
            store.save_esg_engagement_incident({**BASE,"progress":"nope"})
    def test_retention_enum(self):
        with self.assertRaises(ValueError):
            store.save_esg_engagement_incident({**BASE,"retention_decision":"nope"})
    def test_append_only(self):
        store.save_esg_engagement_incident(BASE)
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE esg_engagement_incidents SET progress='closed'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM esg_engagement_incidents WHERE customer_id=? ",("northstar",))
    def test_versioned(self):
        store.save_esg_engagement_incident(BASE)
        store.save_esg_engagement_incident({**BASE,"rationale":"herzien"})
        with store.connect() as db:
            vers=[r["version"] for r in db.execute("SELECT version FROM esg_engagement_incidents WHERE customer_id=? AND fund_ref=?",
                ("northstar","SYNTHETIC-FUND-001")).fetchall()]
        self.assertEqual(sorted(vers),[1,2])
    def test_query(self):
        store.save_esg_engagement_incident(BASE)
        res=store.esg_engagement_incidents(customer_id="northstar",severity="medium")
        self.assertEqual(len(res),1)

if __name__=="__main__":
    unittest.main()
