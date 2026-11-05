"""Feature 51 — BENCH-002 bitemporele benchmarkwijziging tests."""
import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="bench002-") + "/t.db")
from app import store


def isolated_db():
    h, p = tempfile.mkstemp(suffix=".db")
    os.close(h)
    os.unlink(p)
    store.DB_PATH = Path(p)
    store.init()


class Bench002TestCase(unittest.TestCase):
    def setUp(self):
        isolated_db()

    def _save(self, **kw):
        data = {"customer_id": "northstar", "return_type": "total", "actor": "tester", "source_ref": "synth"}
        data.update(kw)
        return store.save_benchmark(data)

    def test_effective_date_defaults_to_valid_from(self):
        r = self._save(valid_from="2026-02-01")
        self.assertEqual(r["effective_date"], "2026-02-01")

    def test_history_policy_validation(self):
        with self.assertRaises(ValueError):
            self._save(history_policy="bogus")

    def test_history_policy_revise_link(self):
        r1 = self._save(history_policy="revise")
        r2 = self._save(history_policy="link")
        self.assertEqual(r1["history_policy"], "revise")
        self.assertEqual(r2["history_policy"], "link")

    def test_known_at_defaults_to_stamp(self):
        r = self._save()
        self.assertTrue(r["known_at"])

    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            self._save(customer_id="nope")

    def test_missing_required(self):
        with self.assertRaises(ValueError):
            store.save_benchmark({"customer_id": "northstar"})

    def test_append_only_update_delete(self):
        self._save()
        with store.connect() as db:
            with self.assertRaises(Exception):
                db.execute("UPDATE benchmark_versions SET name='x'")
            with self.assertRaises(Exception):
                db.execute("DELETE FROM benchmark_versions")

    def test_export_fields(self):
        self._save(effective_date="2026-03-01", history_policy="revise", known_at="2026-03-02T00:00:00Z")
        exp = store.benchmark_export(customer_id="northstar")
        self.assertTrue(exp)
        row = exp[0]
        self.assertIn("effective_date", row)
        self.assertIn("history_policy", row)
        self.assertIn("known_at", row)
        self.assertEqual(row["history_policy"], "revise")


if __name__ == "__main__":
    unittest.main()
