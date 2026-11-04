import os, sys, tempfile, sqlite3, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="re-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",report_ref="RPT-2025-Q1",calendar_period="2025-Q1",deadline="2025-04-15",delivery_status="delivered",completeness="complete",data_quality_errors=None,delay_days=0,incident_ref=None,recovery_action=None,escalation="none",approved_report_ref="RPT-2025-Q1-FINAL",schema_version="1",methodology_version="1.0",source_ref="SYNTHETIC-SRC",rationale="ok")

class RE(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()
    def test_save_basic(self):
        r=store.save_reporting_execution(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["delivery_status"],"delivered")
    def test_required(self):
        for key in ("customer_id","report_ref","calendar_period","deadline","delivery_status","completeness","source_ref","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_reporting_execution(d)
    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_reporting_execution({**BASE,"customer_id":"unknown"})
    def test_status_enum(self):
        with self.assertRaises(ValueError):
            store.save_reporting_execution({**BASE,"delivery_status":"nope"})
    def test_escalation_enum(self):
        with self.assertRaises(ValueError):
            store.save_reporting_execution({**BASE,"escalation":"nope"})
    def test_append_only(self):
        store.save_reporting_execution(BASE)
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE reporting_executions SET completeness='x'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM reporting_executions WHERE customer_id=? ",("northstar",))
    def test_versioned(self):
        store.save_reporting_execution(BASE)
        store.save_reporting_execution({**BASE,"delay_days":3})
        with store.connect() as db:
            vers=[r["version"] for r in db.execute("SELECT version FROM reporting_executions WHERE customer_id=? ",("northstar",)).fetchall()]
        self.assertEqual(sorted(vers),[1,2])
    def test_query(self):
        store.save_reporting_execution(BASE)
        res=store.reporting_executions(customer_id="northstar",report_ref="RPT-2025-Q1",delivery_status="delivered")
        self.assertEqual(len(res),1)

if __name__=="__main__":
    unittest.main()