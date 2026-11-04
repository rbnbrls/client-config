import os, sys, tempfile, sqlite3, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="wtp-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

# WTP-001 Transitieprofiel: fondsregeling/transitiefase, planning, scope,
# relevante besluit-/go-live-/invaardata en eigenaar. Synthetische gegevens.
BASE=dict(customer_id="northstar",fund_ref="FUND-SYNTH-01",fund_regulation="TRA-SYNTH-2026-01",
    transition_phase="migration",planning="2026-Q3 t/m 2027-Q1 (synthetische transitiekalender)",
    scope="Invaar mandaat M-SYNTH-01 incl. bijbehorende rapportageprofielen",
    decision_date="2026-09-15",golive_date="2026-11-02",migration_date="2026-10-18",
    owner="Client Service (synthetisch voorbeeldeigenaar)",source_ref="SYNTHETIC-SRC",rationale="ok")

class WTPTransitionProfiles(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()

    def test_save_basic(self):
        r=store.save_wtp_transition_profile(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["transition_phase"],"migration")
        self.assertEqual(r["fund_regulation"],BASE["fund_regulation"])
        self.assertEqual(r["owner"],BASE["owner"])
        self.assertEqual(r["decision_date"],"2026-09-15")
        self.assertEqual(r["golive_date"],"2026-11-02")
        self.assertEqual(r["migration_date"],"2026-10-18")

    def test_required(self):
        for key in ("customer_id","fund_ref","fund_regulation","transition_phase","planning","scope","owner","source_ref","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_wtp_transition_profile(d)

    def test_empty_string_rejected_for_required(self):
        with self.assertRaises(ValueError):
            store.save_wtp_transition_profile({**BASE,"scope":"   "})

    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_wtp_transition_profile({**BASE,"customer_id":"unknown"})

    def test_phase_enum(self):
        with self.assertRaises(ValueError):
            store.save_wtp_transition_profile({**BASE,"transition_phase":"nope"})

    def test_dates_optional(self):
        r=store.save_wtp_transition_profile({**BASE,"decision_date":None,"golive_date":None,"migration_date":None})
        self.assertIsNone(r["decision_date"]); self.assertIsNone(r["golive_date"]); self.assertIsNone(r["migration_date"])

    def test_dates_whitespace_become_none(self):
        r=store.save_wtp_transition_profile({**BASE,"decision_date":"  ","golive_date":" ","migration_date":""})
        self.assertIsNone(r["decision_date"]); self.assertIsNone(r["golive_date"]); self.assertIsNone(r["migration_date"])

    def test_append_only(self):
        store.save_wtp_transition_profile(BASE)
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE wtp_transition_profiles SET scope='x'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM wtp_transition_profiles WHERE customer_id=?",("northstar",))

    def test_versioned_preserves_previous_phase(self):
        store.save_wtp_transition_profile(BASE)
        store.save_wtp_transition_profile({**BASE,"transition_phase":"golive","rationale":"fase opgeschoven"})
        with store.connect() as db:
            rows=db.execute("SELECT version,transition_phase FROM wtp_transition_profiles WHERE customer_id=? ORDER BY version",("northstar",)).fetchall()
        self.assertEqual([r["version"] for r in rows],[1,2])
        self.assertEqual(rows[0]["transition_phase"],"migration")
        self.assertEqual(rows[1]["transition_phase"],"golive")

    def test_same_fund_id_new_profile_distinct(self):
        store.save_wtp_transition_profile(BASE)
        store.save_wtp_transition_profile({**BASE,"id":"wtp-second","fund_ref":"FUND-SYNTH-02"})
        with store.connect() as db:
            ids=[r["id"] for r in db.execute("SELECT id FROM wtp_transition_profiles WHERE customer_id=? ORDER BY id",("northstar",)).fetchall()]
        self.assertEqual(len(set(ids)),2)

    def test_audit_written(self):
        store.save_wtp_transition_profile(BASE)
        with store.connect() as db:
            row=db.execute("SELECT * FROM audit WHERE entity_id LIKE 'wtp-%' ORDER BY id DESC LIMIT 1").fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["entity_type"],"wtp_transition_profiles")
        self.assertEqual(row["action"],"created")

    def test_query_filters(self):
        store.save_wtp_transition_profile(BASE)
        store.save_wtp_transition_profile({**BASE,"id":"wtp-second","transition_phase":"aftercare"})
        res=store.wtp_transition_profiles(customer_id="northstar",fund_ref="FUND-SYNTH-01",transition_phase="migration")
        self.assertEqual(len(res),1)
        self.assertEqual(res[0]["fund_ref"],"FUND-SYNTH-01")
        res=store.wtp_transition_profiles(owner=BASE["owner"])
        self.assertEqual(len(res),2)

if __name__=="__main__":
    unittest.main()
