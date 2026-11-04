"""CFG-002 Bitemporele revisies — controls/beleid regression tests.

Covers the prototype acceptance criteria from docs/PROJECT-PLAN.md (P1 /
CFG-002, controls slice): time-travel per control code on valid_at/known_at,
source reviews and decisions bounded by transaction time, append-only
triggers on controls/source reviews/decisions, and the synthetic control with
effective date 2026-11-10 that is absent before registration and before its
effective date and present afterwards.

All data is synthetic. Each test runs against an isolated SQLite database.
"""
import os, sys, tempfile, unittest, sqlite3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="cfg002pol-") + "/t.db")
from app import store


def isolated_db():
    handle, path = tempfile.mkstemp(suffix=".db", prefix="cfg002pol-")
    os.close(handle)
    os.unlink(path)
    store.DB_PATH = Path(path)
    store.init()


class PolicyBitemporalTestCase(unittest.TestCase):
    def setUp(self):
        isolated_db()

    def make_control(self, code="CTRL-001", effective="2026-11-10", actor="demo.policy-owner"):
        return store.save_policy({
            "control_code": code,
            "title": f"Synthetisch control {code}",
            "owner": "Compliance (te bevestigen)",
            "audience": "Klant / mandaat",
            "source_ref": "Synthetische bronreferentie (voorbeeld)",
            "applicability": "Alleen synthetisch voorbeeld",
            "enforcement": "manual",
            "effective_date": effective,
            "review_date": "2027-11-10",
            "actor": actor,
            "rationale": "Synthetische registratie",
            "change_note": "Eerste registratie",
        })

    def test_control_absent_before_registration_and_effective_date(self):
        ctrl = self.make_control()
        code = ctrl["control_code"]
        created = ctrl["created_at"]
        rows = store.policies_as_of("2026-11-15", "2020-01-01T00:00:00Z")
        self.assertFalse(any(r["control_code"] == code for r in rows))
        rows = store.policies_as_of("2026-11-05", created)
        self.assertFalse(any(r["control_code"] == code for r in rows))
        rows = store.policies_as_of("2026-11-15", created)
        self.assertTrue(any(r["control_code"] == code for r in rows))

    def test_control_present_only_after_effective_date(self):
        ctrl = self.make_control(effective="2026-11-10")
        code = ctrl["control_code"]
        created = ctrl["created_at"]
        rows = store.policies_as_of("2026-11-10", created)
        self.assertTrue(any(r["control_code"] == code for r in rows))
        rows = store.policies_as_of("2026-11-09", created)
        self.assertFalse(any(r["control_code"] == code for r in rows))

    def test_later_source_review_not_in_older_snapshot(self):
        ctrl = self.make_control(code="SR-CTRL")
        store.add_policy_source_review("SR-CTRL", 1, {
            "source_kind": "primary_regulatory",
            "source_title": "Synthetische primaire bron",
            "source_locator": "SYNTHETIC-LOCATOR-001",
            "outcome": "verified",
            "reviewer": "demo.source-reviewer",
            "reviewer_role": "compliance",
            "rationale": "Synthetische bronreview",
        })
        with store.connect() as db:
            checked = db.execute("SELECT checked_at FROM policy_source_reviews WHERE control_code='SR-CTRL'").fetchone()["checked_at"]
        created = ctrl["created_at"]
        rows = store.policies_as_of("2026-11-15", created)
        r = [x for x in rows if x["control_code"] == "SR-CTRL"][0]
        self.assertIsNone(r["latest_source_review"])
        rows = store.policies_as_of("2026-11-15", checked)
        r = [x for x in rows if x["control_code"] == "SR-CTRL"][0]
        self.assertIsNotNone(r["latest_source_review"])

    def test_later_decision_not_in_older_snapshot(self):
        ctrl = self.make_control(code="DEC-CTRL")
        store.add_policy_source_review("DEC-CTRL", 1, {
            "source_kind": "primary_regulatory",
            "source_title": "Synthetische primaire bron",
            "source_locator": "SYNTHETIC-LOCATOR-001",
            "outcome": "verified",
            "reviewer": "demo.source-reviewer",
            "reviewer_role": "compliance",
            "rationale": "Synthetische bronreview",
        })
        store.decide_policy("DEC-CTRL", 1, {
            "decision": "validated",
            "reviewer": "demo.policy-approver",
            "reviewer_role": "legal",
            "rationale": "Synthetisch besluit",
        })
        with store.connect() as db:
            decided = db.execute("SELECT decided_at FROM policy_decisions WHERE control_code='DEC-CTRL'").fetchone()["decided_at"]
            reviewed = db.execute("SELECT checked_at FROM policy_source_reviews WHERE control_code='DEC-CTRL'").fetchone()["checked_at"]
        created = ctrl["created_at"]
        rows = store.policies_as_of("2026-11-15", reviewed)
        r = [x for x in rows if x["control_code"] == "DEC-CTRL"][0]
        self.assertIsNotNone(r["latest_source_review"])
        self.assertIsNone(r["decision"])
        self.assertEqual(r["validation_status"], "pending")
        rows = store.policies_as_of("2026-11-15", decided)
        r = [x for x in rows if x["control_code"] == "DEC-CTRL"][0]
        self.assertIsNotNone(r["decision"])
        self.assertEqual(r["validation_status"], "validated")

    def test_newer_source_review_flips_validated_to_pending_historically(self):
        ctrl = self.make_control(code="FLIP-CTRL")
        store.add_policy_source_review("FLIP-CTRL", 1, {
            "source_kind": "primary_regulatory",
            "source_title": "Synthetische primaire bron",
            "source_locator": "SYNTHETIC-LOCATOR-001",
            "outcome": "verified",
            "reviewer": "demo.source-reviewer",
            "reviewer_role": "compliance",
            "rationale": "Synthetische bronreview",
        })
        store.decide_policy("FLIP-CTRL", 1, {
            "decision": "validated",
            "reviewer": "demo.policy-approver",
            "reviewer_role": "legal",
            "rationale": "Synthetisch besluit",
        })
        with store.connect() as db:
            decided = db.execute("SELECT decided_at FROM policy_decisions WHERE control_code='FLIP-CTRL'").fetchone()["decided_at"]
        store.add_policy_source_review("FLIP-CTRL", 1, {
            "source_kind": "primary_regulatory",
            "source_title": "Synthetische primaire bron 2",
            "source_locator": "SYNTHETIC-LOCATOR-002",
            "outcome": "insufficient",
            "reviewer": "demo.other-reviewer",
            "reviewer_role": "compliance",
            "rationale": "Nieuwere review",
        })
        with store.connect() as db:
            newer_review = db.execute(
                "SELECT checked_at FROM policy_source_reviews WHERE control_code='FLIP-CTRL' ORDER BY checked_at DESC LIMIT 1"
            ).fetchone()["checked_at"]
        rows = store.policies_as_of("2026-11-15", decided)
        r = [x for x in rows if x["control_code"] == "FLIP-CTRL"][0]
        self.assertEqual(r["validation_status"], "validated")
        rows = store.policies_as_of("2026-11-15", newer_review)
        r = [x for x in rows if x["control_code"] == "FLIP-CTRL"][0]
        self.assertEqual(r["validation_status"], "pending")

    def test_echoes_valid_at_and_known_at(self):
        self.make_control(code="ECHO-CTRL")
        created = store.policies("ECHO-CTRL")[0]["created_at"]
        rows = store.policies_as_of("2026-11-15", created)
        r = [x for x in rows if x["control_code"] == "ECHO-CTRL"][0]
        self.assertEqual(r["valid_at"], "2026-11-15")
        self.assertEqual(r["known_at"], created)

    def test_append_only_triggers_block_update_and_delete(self):
        self.make_control(code="TRIG-CTRL")
        store.add_policy_source_review("TRIG-CTRL", 1, {
            "source_kind": "primary_regulatory",
            "source_title": "Synthetische primaire bron",
            "source_locator": "SYNTHETIC-LOCATOR-001",
            "outcome": "verified",
            "reviewer": "demo.source-reviewer",
            "reviewer_role": "compliance",
            "rationale": "Synthetische bronreview",
        })
        store.decide_policy("TRIG-CTRL", 1, {
            "decision": "validated",
            "reviewer": "demo.policy-approver",
            "reviewer_role": "legal",
            "rationale": "Synthetisch besluit",
        })
        with store.connect() as db:
            cid = db.execute("SELECT id FROM policy_controls WHERE control_code='TRIG-CTRL'").fetchone()["id"]
            rid = db.execute("SELECT id FROM policy_source_reviews WHERE control_code='TRIG-CTRL'").fetchone()["id"]
            did = db.execute("SELECT id FROM policy_decisions WHERE control_code='TRIG-CTRL'").fetchone()["id"]
            cases = [
                "UPDATE policy_controls SET title='x' WHERE id=?",
                "DELETE FROM policy_controls WHERE id=?",
                "UPDATE policy_source_reviews SET rationale='x' WHERE id=?",
                "DELETE FROM policy_source_reviews WHERE id=?",
                "UPDATE policy_decisions SET rationale='x' WHERE id=?",
                "DELETE FROM policy_decisions WHERE id=?",
            ]
            vals = [cid, cid, rid, rid, did, did]
            for sql, val in zip(cases, vals):
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute(sql, (val,))
                    db.commit()

    def test_version_selection_by_effective_date_and_version(self):
        v1 = self.make_control(code="VER-CTRL", effective="2026-01-01")
        v2 = store.save_policy({
            "control_code": "VER-CTRL",
            "title": "Synthetisch control v2",
            "owner": "Compliance (te bevestigen)",
            "audience": "Klant / mandaat",
            "source_ref": "Synthetische bronreferentie (voorbeeld)",
            "applicability": "Alleen synthetisch voorbeeld",
            "enforcement": "manual",
            "effective_date": "2026-06-01",
            "review_date": "2027-01-01",
            "actor": "demo.policy-owner",
            "rationale": "Nieuwe versie",
            "change_note": "Revisie",
        }, control_code="VER-CTRL")
        created_v2 = v2["created_at"]
        rows = store.policies_as_of("2026-03-01", created_v2)
        r = [x for x in rows if x["control_code"] == "VER-CTRL"][0]
        self.assertEqual(r["version"], 1)
        rows = store.policies_as_of("2026-07-01", created_v2)
        r = [x for x in rows if x["control_code"] == "VER-CTRL"][0]
        self.assertEqual(r["version"], 2)
        rows = store.policies_as_of("2026-07-01", v1["created_at"])
        r = [x for x in rows if x["control_code"] == "VER-CTRL"][0]
        self.assertEqual(r["version"], 1)

    def test_known_at_second_precision_includes_subsecond(self):
        ctrl = self.make_control(code="SUB-CTRL")
        created = ctrl["created_at"]
        second_precision = created[:19] + "Z"
        rows = store.policies_as_of("2026-11-15", second_precision)
        self.assertTrue(any(r["control_code"] == "SUB-CTRL" for r in rows))


if __name__ == "__main__":
    unittest.main()
