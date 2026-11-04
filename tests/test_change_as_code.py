import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="cac-") + "/t.db")
from app import store

def isolated_db():
    h, p = tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH = Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar", "Northstar", "pension", "NL", "institutional", store.now()))

BASE = dict(customer_id="northstar", entity_type="policy", entity_ref="POL-001",
    base_version="v1", effective_from="2026-01-01", diff='{"added":"x"}',
    rationale="rationale", evidence_ref="EVD-1", schema_version="schema-1",
    policy_version="policy-1", source_ref="SRC-1")

class ChangeAsCode(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()

    def test_save_basic(self):
        r = store.save_change_as_code(BASE)
        self.assertEqual(r["version"], 1)
        self.assertEqual(r["entity_type"], "policy")

    def test_required(self):
        for key in store.CHANGE_AS_CODE_REQUIRED:
            d = dict(BASE); d[key] = None
            with self.assertRaises(ValueError):
                store.save_change_as_code(d)

    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_change_as_code({**BASE, "customer_id": "unknown"})

    def test_append_only(self):
        store.save_change_as_code(BASE)
        with store.connect() as db:
            with self.assertRaises(Exception):
                db.execute("UPDATE change_as_code SET diff='y'")
            with self.assertRaises(Exception):
                db.execute("DELETE FROM change_as_code")

    def test_versioning(self):
        store.save_change_as_code(BASE)
        r2 = store.save_change_as_code({**BASE, "diff": '{"changed":"y"}'})
        self.assertEqual(r2["version"], 2)

    def test_export(self):
        store.save_change_as_code(BASE)
        ex = store.change_as_code_export(customer_id="northstar")
        self.assertEqual(ex["coverage"], 1)
        self.assertIn("perimeter", ex)
        self.assertIn("generated_at", ex)

    def test_list_filter(self):
        store.save_change_as_code(BASE)
        store.save_change_as_code({**BASE, "entity_type": "schema", "entity_ref": "S-1"})
        rows = store.change_as_code(customer_id="northstar", entity_type="schema")
        self.assertEqual(len(rows), 1)

if __name__ == "__main__":
    unittest.main()
