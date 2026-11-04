import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="cv-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

class CV(unittest.TestCase):
    def setUp(self): isolated_db()
    def make_policy(self):
        return store.save_policy({"control_code":"C1","title":"t","owner":"o","audience":"a","source_ref":"s","applicability":"ap","enforcement":"manual","effective_date":"2026-01-01","review_date":"2027-01-01","actor":"owner","rationale":"r"})
    def test_fk(self):
        self.make_policy()
        with self.assertRaises(ValueError):
            store.save_client_variant({"control_code":"NOPE","policy_version":1,"client_id":"x","contractual_requirement":"r","source_ref":"s","reconciliation_status":"manual_review","effective_date":"2026-01-01","owner":"o","rationale":"r"})
    def test_append_only(self):
        self.make_policy()
        v=store.save_client_variant({"control_code":"C1","policy_version":1,"client_id":"c","contractual_requirement":"r","source_ref":"s","reconciliation_status":"manual_review","effective_date":"2026-01-01","owner":"o","rationale":"r"})
        store.save_client_variant({"id":v["id"],"control_code":"C1","policy_version":1,"client_id":"c","contractual_requirement":"r2","source_ref":"s","reconciliation_status":"manual_review","effective_date":"2026-02-01","owner":"o","rationale":"corr"})
        vers=[r["version"] for r in store.client_variants() if r["id"]==v["id"]]
        self.assertEqual(sorted(vers),[1,2])
    def test_signals_nonblocking(self):
        self.make_policy()
        store.save_client_variant({"control_code":"C1","policy_version":1,"client_id":"c","contractual_requirement":"r","source_ref":"s","reconciliation_status":"manual_review","effective_date":"2026-01-01","owner":"o","rationale":"r"})
        sigs=store.client_variant_signals()
        self.assertTrue(all(s["blocking"] is False for s in sigs))

if __name__=="__main__":
    unittest.main()
