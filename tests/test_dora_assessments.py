import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="da-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

BASE=dict(counterparty="Synth Supplier", service_name="svc", scope_description="scope", applicability="pending_review", criticality="unassessed", contract_ref="CTR-1", source_ref="SRC-1", reviewer="demo.compliance", reviewer_role="compliance", rationale="r", review_date="2027-01-01", effective_from="2026-01-01")

class DA(unittest.TestCase):
    def setUp(self): isolated_db()
    def test_three_perimeters(self):
        for t in ("managed_activity","supplier_ict","platform_ict"):
            d=store.save_dora_assessment({**BASE,"assessment_type":t})
            self.assertEqual(d["assessment_type"],t)
    def test_append_only(self):
        d=store.save_dora_assessment({**BASE,"assessment_type":"supplier_ict"})
        store.save_dora_assessment({**d,"rationale":"corr","applicability":"in_scope"})
        with store.connect() as db:
            vers=[r["version"] for r in db.execute("SELECT version FROM dora_assessments WHERE id=?",(d["id"],)).fetchall()]
        self.assertEqual(sorted(vers),[1,2])
    def test_platform_no_customer(self):
        d=store.save_dora_assessment({**BASE,"assessment_type":"platform_ict","customer_id":""})
        self.assertIsNone(d["customer_id"])
    def test_invalid_type(self):
        with self.assertRaises(ValueError):
            store.save_dora_assessment({**BASE,"assessment_type":"nope"})
    def test_delete_blocked(self):
        d=store.save_dora_assessment({**BASE,"assessment_type":"managed_activity"})
        import sqlite3
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM dora_assessments WHERE id=?",(d["id"],))
    def test_valid_time_filter(self):
        d=store.save_dora_assessment({**BASE,"assessment_type":"managed_activity","effective_from":"2026-06-01"})
        rows=store.dora_assessments(valid_at="2026-05-01", known_at="2099-01-01T00:00:00Z")
        self.assertFalse(any(r["id"]==d["id"] for r in rows))
        rows=store.dora_assessments(valid_at="2026-07-01", known_at="2099-01-01T00:00:00Z")
        self.assertTrue(any(r["id"]==d["id"] for r in rows))

if __name__=="__main__":
    unittest.main()