import os, sys, tempfile, unittest, sqlite3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="ipr-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

BASE=dict(provider="Synth ICT", ict_service="svc", function_classification="critical", contract_ref="CTR-1", incident_evidence="INC-1", exit_evidence="EXIT-1", applicability="pending_review", source_ref="SRC-1", reviewer="demo.compliance", reviewer_role="compliance", rationale="r", review_date="2027-01-01", effective_from="2026-01-01")

class IPR(unittest.TestCase):
    def setUp(self): isolated_db()
    def test_three_classifications(self):
        for c in ("critical","important","other"):
            d=store.save_ict_provider_relation({**BASE,"function_classification":c})
            self.assertEqual(d["function_classification"],c)
    def test_append_only(self):
        d=store.save_ict_provider_relation({**BASE})
        store.save_ict_provider_relation({**d,"rationale":"corr","applicability":"in_scope"})
        with store.connect() as db:
            vers=[r["version"] for r in db.execute("SELECT version FROM ict_provider_relations WHERE id=?",(d["id"],)).fetchall()]
        self.assertEqual(sorted(vers),[1,2])
    def test_platform_no_customer(self):
        d=store.save_ict_provider_relation({**BASE,"customer_id":""})
        self.assertIsNone(d["customer_id"])
    def test_invalid_classification(self):
        with self.assertRaises(ValueError):
            store.save_ict_provider_relation({**BASE,"function_classification":"nope"})
    def test_delete_blocked(self):
        d=store.save_ict_provider_relation({**BASE})
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM ict_provider_relations WHERE id=?",(d["id"],))
    def test_valid_time_filter(self):
        d=store.save_ict_provider_relation({**BASE,"effective_from":"2026-06-01"})
        rows=store.ict_provider_relations(valid_at="2026-05-01", known_at="2099-01-01T00:00:00Z")
        self.assertFalse(any(r["id"]==d["id"] for r in rows))
        rows=store.ict_provider_relations(valid_at="2026-07-01", known_at="2099-01-01T00:00:00Z")
        self.assertTrue(any(r["id"]==d["id"] for r in rows))
    def test_customer_not_found(self):
        with self.assertRaises(ValueError):
            store.save_ict_provider_relation({**BASE,"customer_id":"nope"})
    def test_missing_required(self):
        for k in BASE:
            bad=dict(BASE); bad[k]=""
            with self.assertRaises(ValueError):
                store.save_ict_provider_relation(bad)

if __name__=="__main__":
    unittest.main()
