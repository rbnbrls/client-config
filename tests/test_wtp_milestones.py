import os, sys, tempfile, sqlite3, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="wtp-ms-")+ "/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",fund_ref="FUND-SYNTH-01",deliverable="Migratieplan (synthetisch)",
    validation_criteria="Alle deelnemers gemigreerd",source_ref="SYNTHETIC-SRC",rationale="ok",
    planning="2026-Q3",progress_report="maandelijks",risk_impact="vertraging op golive",
    recovery_plan="fallback handmatig",go_no_go_evidence="gezamenlijk dossier",evidence_status="open")

class WTPMilestones(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()

    def test_save_basic(self):
        r=store.save_wtp_milestone(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["deliverable"],BASE["deliverable"])
        self.assertEqual(r["validation_criteria"],BASE["validation_criteria"])
        self.assertEqual(r["evidence_status"],"open")

    def test_required(self):
        for key in ("customer_id","fund_ref","deliverable","validation_criteria","source_ref","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_wtp_milestone(d)

    def test_empty_string_rejected_for_required(self):
        with self.assertRaises(ValueError):
            store.save_wtp_milestone({**BASE,"deliverable":"   "})

    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_wtp_milestone({**BASE,"customer_id":"unknown"})

    def test_evidence_status_enum(self):
        with self.assertRaises(ValueError):
            store.save_wtp_milestone({**BASE,"evidence_status":"nope"})

    def test_optional_fields_none(self):
        r=store.save_wtp_milestone({**BASE,"planning":None,"progress_report":None,"risk_impact":None,"recovery_plan":None,"go_no_go_evidence":None,"evidence_status":None})
        for k in ("planning","progress_report","risk_impact","recovery_plan","go_no_go_evidence","evidence_status"):
            self.assertIsNone(r[k])

    def test_versioning_and_append_only(self):
        store.save_wtp_milestone(BASE)
        r2=store.save_wtp_milestone({**BASE,"validation_criteria":"Nieuwe criteria"})
        self.assertEqual(r2["version"],2)
        rows=store.wtp_milestones(customer_id="northstar",fund_ref="FUND-SYNTH-01")
        self.assertEqual(len(rows),2)
        import sqlite3
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE wtp_milestones SET deliverable='x' WHERE id=?",(r2["id"],))
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM wtp_milestones WHERE id=?",(r2["id"],))

    def test_query_filters(self):
        store.save_wtp_milestone(BASE)
        store.save_wtp_milestone({**BASE,"deliverable":"Eindrapportage (synthetisch)","evidence_status":"validated"})
        self.assertEqual(len(store.wtp_milestones(evidence_status="open")),1)
        self.assertEqual(len(store.wtp_milestones(evidence_status="validated")),1)

if __name__=="__main__":
    unittest.main()
