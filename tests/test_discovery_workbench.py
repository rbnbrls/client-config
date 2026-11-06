"""F01 discovery workbench API and append-only decision records.

All values are synthetic. Formal pilot, owner and legal decisions remain open.
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="discovery-") + "/t.db")
from app import store


class DiscoveryWorkbenchTestCase(unittest.TestCase):
    def setUp(self):
        handle, path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        Path(path).unlink()
        store.DB_PATH = Path(path)
        store.init()

    def test_catalog_is_explicitly_open_and_synthetic(self):
        catalog = store.discovery_catalog()
        self.assertEqual(catalog["pilot"]["status"], "open")
        self.assertIn("synthetisch", catalog["pilot"]["name"])
        self.assertEqual(len(catalog["chain"]), 4)
        self.assertTrue(catalog["data_dictionary"])
        self.assertTrue(catalog["policy_owners"])
        self.assertTrue(catalog["adr_decisions"])

    def test_decision_is_append_only_and_audited(self):
        saved = store.save_discovery_decision({
            "decision_key": "pilot.profile",
            "status": "open",
            "decision": "Pilot blijft synthetisch tot klant-/mandaat-eigenaar bevestigt",
            "owner": "Klant-/mandaat-eigenaar",
            "rationale": "Menselijke bevestiging ontbreekt",
            "actor": "synthetic.discovery-reviewer",
        })
        self.assertEqual(saved["version"], 1)
        revised = store.save_discovery_decision({
            "decision_key": "pilot.profile",
            "status": "confirmed",
            "decision": "Synthetisch pilotprofiel bevestigd voor demo",
            "owner": "synthetic.product-owner",
            "rationale": "Beperkt tot lokale demo",
            "actor": "synthetic.discovery-approver",
        })
        self.assertEqual(revised["version"], 2)
        self.assertEqual([row["version"] for row in store.discovery_decisions("pilot.profile")], [2, 1])
        audit = [row for row in store.audit_log() if row["entity_type"] == "discovery_decision"]
        self.assertEqual(len(audit), 2)
        self.assertEqual(audit[0]["new_value"]["status"], "confirmed")

    def test_invalid_status_is_rejected(self):
        with self.assertRaises(ValueError):
            store.save_discovery_decision({
                "decision_key": "adr.0002",
                "status": "approved",
                "decision": "Niet toegestaan",
                "owner": "synthetic.owner",
                "rationale": "synthetic",
                "actor": "synthetic.actor",
            })


if __name__ == "__main__":
    unittest.main()
