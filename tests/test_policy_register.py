"""Regression tests for the POL-001 besluitenregister (append-only policy decision register).

All data is synthetic. Each test runs against an isolated SQLite database so the
prototype demo database is never touched.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="pol001-tests-") + "/test.db")

from app import store  # noqa: E402

# Synthetic actors; distinct persons on purpose (vier-ogen-principe).
OWNER = "demo.policy-owner"
SOURCE_REVIEWER = "demo.source-reviewer"
OTHER_REVIEWER = "demo.other-reviewer"
APPROVER = "demo.policy-approver"


def isolated_db():
    handle, path = tempfile.mkstemp(suffix=".db", prefix="pol001-")
    os.close(handle)
    os.unlink(path)
    store.DB_PATH = Path(path)
    store.init()


class PolicyRegisterTestCase(unittest.TestCase):
    def setUp(self):
        isolated_db()

    def make_policy(self, code, enforcement="hard"):
        return store.save_policy({
            "control_code": code,
            "title": f"Synthetisch control {code}",
            "owner": "Compliance (te bevestigen)",
            "audience": "Klant / mandaat",
            "source_ref": "Synthetische bronreferentie (voorbeeld)",
            "applicability": "Alleen synthetisch voorbeeld",
            "enforcement": enforcement,
            "effective_date": "2026-11-01",
            "review_date": "2027-11-01",
            "actor": OWNER,
            "rationale": "Synthetische registratie",
        })

    def verify_source(self, code, version, reviewer=SOURCE_REVIEWER, role="compliance",
                      outcome="verified", kind="primary_regulatory"):
        return store.add_policy_source_review(code, version, {
            "source_kind": kind,
            "source_title": "Synthetische primaire bron",
            "source_locator": "SYNTHETIC-LOCATOR-001",
            "outcome": outcome,
            "reviewer": reviewer,
            "reviewer_role": role,
            "rationale": "Synthetische bronreview",
        })

    def decide(self, code, version, reviewer=APPROVER, role="legal", decision="validated"):
        return store.decide_policy(code, version, {
            "decision": decision,
            "reviewer": reviewer,
            "reviewer_role": role,
            "rationale": "Synthetisch besluit",
        })

    def latest(self, code):
        return store.policies(code)[0]

    def delete_review(self, review_id):
        db = store.sqlite3.connect(store.DB_PATH)
        try:
            db.execute("DELETE FROM policy_source_reviews WHERE id=?", (review_id,))
            db.commit()
        finally:
            db.close()

    # --- Acceptance: register read path exposes the full contract -----------
    def test_register_read_path_exposes_full_contract(self):
        p = self.make_policy("READ-PATH-1")
        for key in ("owner", "audience", "source_ref", "applicability", "enforcement",
                    "effective_date", "version", "review_date", "validation_status"):
            self.assertIn(key, p)
        self.assertEqual(p["enforcement"], "hard")
        self.assertEqual(p["validation_status"], "pending")

    # --- Acceptance: hard block refused without validated status + evidence -
    def test_hard_block_refused_without_validated_status_and_evidence(self):
        code = "HARD-GATE-1"
        self.make_policy(code)
        with self.assertRaises(ValueError):
            store.hard_block(code)
        self.verify_source(code, 1)
        with self.assertRaises(ValueError):
            store.hard_block(code)
        self.decide(code, 1)
        allowed = store.hard_block(code)
        self.assertTrue(allowed["blocking"])
        self.assertTrue(allowed["source_review_id"])
        self.assertTrue(allowed["decision_id"])

    def test_hard_block_refused_for_soft_and_manual_enforcement(self):
        for code, level in (("HARD-GATE-2", "soft"), ("HARD-GATE-3", "manual")):
            self.make_policy(code, enforcement=level)
            result = store.hard_block(code)
            self.assertFalse(result["blocking"])

    # --- Acceptance: newer source review flips validated back to pending ----
    def test_newer_source_review_flips_validated_back_to_pending(self):
        code = "FLIP-GATE-1"
        self.make_policy(code)
        self.verify_source(code, 1)
        self.decide(code, 1)
        self.assertEqual(self.latest(code)["validation_status"], "validated")
        self.verify_source(code, 1, reviewer=OTHER_REVIEWER, outcome="insufficient")
        self.assertEqual(self.latest(code)["validation_status"], "pending")
        with self.assertRaises(ValueError):
            store.hard_block(code)

    # --- Acceptance: decision requires a reviewer distinct from source reviewer
    def test_policy_decision_requires_reviewer_distinct_from_source_reviewer(self):
        code = "SEP-GATE-1"
        self.make_policy(code)
        self.verify_source(code, 1)
        with self.assertRaises(ValueError):
            self.decide(code, 1, reviewer=SOURCE_REVIEWER)

    def test_source_review_by_initiator_is_refused(self):
        code = "SEP-GATE-2"
        self.make_policy(code)
        with self.assertRaises(ValueError):
            self.verify_source(code, 1, reviewer=OWNER)

    def test_decision_without_verified_source_review_is_refused(self):
        code = "SEP-GATE-3"
        self.make_policy(code)
        with self.assertRaises(ValueError):
            self.decide(code, 1)
        self.verify_source(code, 1, outcome="insufficient")
        with self.assertRaises(ValueError):
            self.decide(code, 1)

    # --- Acceptance: append-only source-review history stays readable -------
    def test_source_review_history_remains_available_after_later_reviews(self):
        code = "HIST-GATE-1"
        self.make_policy(code)
        first = self.verify_source(code, 1)
        self.decide(code, 1)
        second = self.verify_source(code, 1, reviewer=OTHER_REVIEWER, outcome="insufficient")
        history = store.policy_source_reviews(code, 1)
        ids = [r["id"] for r in history]
        self.assertIn(first[0]["id"], ids)
        self.assertIn(second[-1]["id"], ids)
        self.assertEqual(len(ids), 2)
        with self.assertRaises(sqlite_error()):
            self.delete_review(first[0]["id"])

    # --- Acceptance: unapproved interpretations are non-blocking signals ----
    def test_unapproved_interpretations_surface_as_non_blocking_signals(self):
        code = "SIGNAL-GATE-1"
        self.make_policy(code)
        signals = store.policy_signals()
        match = [s for s in signals if s["control_code"] == code]
        self.assertEqual(len(match), 1)
        self.assertFalse(match[0]["blocking"])
        self.assertEqual(match[0]["severity"], "signal")
        # The signal must not raise or block; hard_block refusing is separate.
        self.assertEqual(self.latest(code)["validation_status"], "pending")

    def test_validated_controls_produce_no_signal(self):
        code = "SIGNAL-GATE-2"
        self.make_policy(code)
        self.verify_source(code, 1)
        self.decide(code, 1)
        self.assertEqual([s for s in store.policy_signals() if s["control_code"] == code], [])


def sqlite_error():
    import sqlite3
    return sqlite3.IntegrityError


if __name__ == "__main__":
    unittest.main()
