import os, sys, tempfile, unittest, sqlite3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="gov-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

BASE=dict(policy="Beleidsdocument", monitoring_frequency="quarterly", reporting="Kwartaalrapportage",
    escalation="Client lead → Beleggingscommissie", independent_evaluation="Jaarlijks extern",
    capacity="2 fte", evaluation_date="2027-01-01", applicability="pending_review",
    source_ref="SRC-1", reviewer="demo.compliance", reviewer_role="compliance",
    rationale="r", review_date="2027-01-01", effective_from="2026-01-01")

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

class GovernancePolicies(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()
    def test_required_fields_missing(self):
        for k in BASE:
            bad=dict(BASE); bad[k]=""
            with self.assertRaises(ValueError):
                store.save_governance_policy(bad)
    def test_invalid_applicability_enum(self):
        with self.assertRaises(ValueError):
            store.save_governance_policy({**BASE,"applicability":"nope"})
    def test_invalid_reviewer_role(self):
        with self.assertRaises(ValueError):
            store.save_governance_policy({**BASE,"reviewer_role":"nope"})
    def test_iso_date_validation(self):
        for k in ("effective_from","review_date","evaluation_date"):
            with self.assertRaises(ValueError):
                store.save_governance_policy({**BASE,k:"01-01-2026"})
    def test_effective_to_before_from_rejected(self):
        with self.assertRaises(ValueError):
            store.save_governance_policy({**BASE,"effective_to":"2025-12-31"})
    def test_effective_to_equal_from_rejected(self):
        with self.assertRaises(ValueError):
            store.save_governance_policy({**BASE,"effective_to":"2026-01-01"})
    def test_effective_to_after_from_accepted(self):
        d=store.save_governance_policy({**BASE,"effective_to":"2026-12-31"})
        self.assertEqual(d["effective_to"],"2026-12-31")
    def test_unknown_customer_rejected(self):
        with self.assertRaises(ValueError):
            store.save_governance_policy({**BASE,"customer_id":"nope"})
    def test_platform_no_customer(self):
        d=store.save_governance_policy({**BASE,"customer_id":""})
        self.assertIsNone(d["customer_id"])
    def test_append_only_update_blocked(self):
        d=store.save_governance_policy({**BASE})
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE governance_policies SET policy='x' WHERE id=?",(d["id"],))
    def test_append_only_delete_blocked(self):
        d=store.save_governance_policy({**BASE})
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM governance_policies WHERE id=?",(d["id"],))
    def test_versioning_max_projection(self):
        d=store.save_governance_policy({**BASE})
        d2=store.save_governance_policy({**d,"policy":"Beleidsdocument v2","applicability":"in_scope"})
        self.assertEqual(d2["version"],2)
        rows=store.governance_policies()
        versions=[r["version"] for r in rows if r["id"]==d["id"]]
        self.assertEqual(versions,[2])
        with store.connect() as db:
            stored=sorted(r["version"] for r in db.execute("SELECT version FROM governance_policies WHERE id=?",(d["id"],)).fetchall())
        self.assertEqual(stored,[1,2])
    def test_valid_time_filter(self):
        d=store.save_governance_policy({**BASE,"effective_from":"2026-06-01"})
        rows=store.governance_policies(valid_at="2026-05-01", known_at="2099-01-01T00:00:00Z")
        self.assertFalse(any(r["id"]==d["id"] for r in rows))
        rows=store.governance_policies(valid_at="2026-07-01", known_at="2099-01-01T00:00:00Z")
        self.assertTrue(any(r["id"]==d["id"] for r in rows))
    def test_known_at_filter_hides_future_rows(self):
        d=store.save_governance_policy({**BASE})
        rows=store.governance_policies(known_at="2000-01-01T00:00:00Z")
        self.assertFalse(any(r["id"]==d["id"] for r in rows))
    def test_customer_filter(self):
        d=store.save_governance_policy({**BASE,"customer_id":"northstar"})
        rows=store.governance_policies(customer_id="northstar")
        self.assertTrue(any(r["id"]==d["id"] for r in rows))
        rows=store.governance_policies(customer_id="someoneelse")
        self.assertFalse(any(r["id"]==d["id"] for r in rows))
    def test_audit_entry_written(self):
        d=store.save_governance_policy({**BASE})
        with store.connect() as db:
            rows=db.execute("SELECT * FROM audit WHERE entity_type=? AND entity_id=?",("governance_policy",d["id"])).fetchall()
        self.assertTrue(rows)
        self.assertEqual(rows[0]["action"],"created")
        d2=store.save_governance_policy({**d,"rationale":"corr"})
        with store.connect() as db:
            rows=db.execute("SELECT action FROM audit WHERE entity_type=? AND entity_id=?",("governance_policy",d["id"])).fetchall()
        self.assertIn("versioned",[r["action"] for r in rows])

if __name__=="__main__":
    unittest.main()
