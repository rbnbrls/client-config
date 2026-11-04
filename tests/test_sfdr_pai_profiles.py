import os, sys, tempfile, sqlite3, unittest, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="pai-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",profile_name="PAI-Profile-1",pai_indicators=["PAI-1","PAI-2"],reference_period="2025",reporting_frequency="annual",methodology="EU-delegated",data_coverage="90%",missing_data_reason="not-available",assurance="limited",responsibility="client-service",applicability_decision_ref="ADR-PAI-001",source_ref="SYNTHETIC-SRC",rationale="pai")

class PAI(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()
    def test_save_basic(self):
        r=store.save_sfdr_pai_profile(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["responsibility"],"client-service")
    def test_required(self):
        for key in ("customer_id","profile_name","pai_indicators","reference_period","reporting_frequency","methodology","data_coverage","missing_data_reason","assurance","responsibility","applicability_decision_ref","source_ref","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_sfdr_pai_profile(d)
    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_sfdr_pai_profile({**BASE,"customer_id":"unknown"})
    def test_freq_enum(self):
        with self.assertRaises(ValueError):
            store.save_sfdr_pai_profile({**BASE,"reporting_frequency":"nope"})
    def test_append_only(self):
        store.save_sfdr_pai_profile(BASE)
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE sfdr_pai_profiles SET methodology='x'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM sfdr_pai_profiles WHERE customer_id=?",("northstar",))
    def test_versioned(self):
        store.save_sfdr_pai_profile(BASE)
        store.save_sfdr_pai_profile({**BASE,"methodology":"revised"})
        with store.connect() as db:
            vers=[r["version"] for r in db.execute("SELECT version FROM sfdr_pai_profiles WHERE customer_id=? ",("northstar",)).fetchall()]
        self.assertEqual(sorted(vers),[1,2])
    def test_query(self):
        store.save_sfdr_pai_profile(BASE)
        res=store.sfdr_pai_profiles(customer_id="northstar",profile_name="PAI-Profile-1",responsibility="client-service")
        self.assertEqual(len(res),1)

if __name__=="__main__":
    unittest.main()
