"""Feature 11 — AUD-001 append-only audit.

Vastgelegde auditrecords bevatten actor, actie, tijd, oude/nieuwe waarde,
reden, bronbewijs, policy-/schema-versie, simulatie, goedkeuring, activatie
en export/publicatiestatus. De audit is append-only: niet bij te werken of
hard te verwijderen, ook niet via de reguliere product-API.

Synthetische gegevens; geen echte klant- of financiële data.
"""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="audit-") + "/t.db")
from app import store


def isolated_db():
    h, p = tempfile.mkstemp(suffix=".db")
    os.close(h)
    os.unlink(p)
    store.DB_PATH = Path(p)
    store.init()


class AuditAppendOnly(unittest.TestCase):
    def setUp(self):
        isolated_db()

    def test_audit_update_is_blocked(self):
        """Records zijn niet bij te werken (append-only)."""
        with store.connect() as db:
            db.execute(
                "INSERT INTO audit(entity_type,entity_id,action,actor,reason,at,details)"
                " VALUES('test','1','created','tester','synthetische probe','2026-01-01T00:00:00Z','{}')"
            )
            with self.assertRaises((sqlite3.OperationalError, sqlite3.IntegrityError)) as ctx:
                db.execute("UPDATE audit SET actor='attacker' WHERE entity_type='test'")
            self.assertIn("append-only", str(ctx.exception))

    def test_audit_delete_is_blocked(self):
        """Records zijn niet hard te verwijderen."""
        with store.connect() as db:
            db.execute(
                "INSERT INTO audit(entity_type,entity_id,action,actor,reason,at,details)"
                " VALUES('test','2','created','tester','synthetische probe','2026-01-01T00:00:00Z','{}')"
            )
            with self.assertRaises((sqlite3.OperationalError, sqlite3.IntegrityError)) as ctx:
                db.execute("DELETE FROM audit WHERE entity_type='test'")
            self.assertIn("append-only", str(ctx.exception))

    def test_audit_log_returns_rich_records(self):
        rows = store.audit_log()
        self.assertTrue(rows)
        for row in rows:
            self.assertIn("actor", row)
            self.assertIn("action", row)
            self.assertIn("at", row)
            self.assertIn("reason", row)
            self.assertIsInstance(row["details"], dict)

    def test_change_set_lifecycle_records_audit_fields(self):
        """created/simulated/approved/activated leggen oude/nieuwe waarde, reden,
        bronbewijs, schema-versie, simulatie, goedkeuring en activatie vast."""
        cid = store.create_change({
            "customer_id": "northstar",
            "base_version": 1,
            "patch": {"fees.bps": 20},
            "effective_date": "2027-01-01",
            "actor": "synthetic.initiator",
            "rationale": "Synthetische tariffwijziging",
        })["id"]
        store.simulate(cid, {"aum_eur": 100_000_000, "actor": "synthetic.initiator"})
        store.approve(cid, {"actor": "synthetic.approver", "reason": "Synthetische goedkeuring"})
        store.activate(cid, {"actor": "synthetic.operator", "reason": "Synthetische activatie"})

        entries = [r for r in store.audit_log() if r["entity_id"] == cid]
        self.assertEqual({e["action"] for e in entries}, {"created", "simulated", "approved", "activated"})

        created = next(e for e in entries if e["action"] == "created")
        self.assertEqual(created["old_value"], {"fees.bps": 18})
        self.assertEqual(created["new_value"], {"fees.bps": 20})
        self.assertTrue(created["evidence"])
        self.assertTrue(created["schema_version"])

        approved = next(e for e in entries if e["action"] == "approved")
        self.assertEqual(approved["approval"]["approved_by"], "synthetic.approver")
        self.assertTrue(approved["simulation"])

        activated = next(e for e in entries if e["action"] == "activated")
        self.assertTrue(activated["activation"])

    def test_export_records_publication_status_audit(self):
        """Audit over export/publicatiestatus van een partnerexport."""
        eid = store.export_config("northstar", "generic-asp", "synthetic.publisher")["export_id"]
        entries = [r for r in store.audit_log() if r["entity_id"] == eid]
        self.assertTrue(entries)
        entry = entries[0]
        self.assertEqual(entry["entity_type"], "export")
        self.assertTrue(entry["publication_status"])
        self.assertTrue(entry["evidence"])


if __name__ == "__main__":
    unittest.main()
