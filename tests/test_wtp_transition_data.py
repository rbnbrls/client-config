import os, sys, tempfile, sqlite3, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="wtp-data-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",fund_ref="FUND-SYNTH-01",data_item="Deelnemersbestand (synthetisch)",
    data_phase="voor",owner="Fonds",source="PUO",frequency="maandelijks",
    validation_rule="Volledigheid en unieke ID",source_ref="SYNTHETIC-SRC",rationale="ok",
    reconciliation="afstemming met custodian",data_quality_norm=">=99% volledig",
    evidence="testbestand",continuity_agreement="fallback via handmatige upload")

class WTPTransitionData(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()

    def test_save_basic(self):
        r=store.save_wtp_transition_data(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["data_phase"],"voor")
        self.assertEqual(r["data_item"],BASE["data_item"])
        self.assertEqual(r["owner"],"Fonds")
        self.assertEqual(r["frequency"],"maandelijks")
        self.assertEqual(r["validation_rule"],BASE["validation_rule"])
        self.assertEqual(r["reconciliation"],BASE["reconciliation"])
        self.assertEqual(r["continuity_agreement"],BASE["continuity_agreement"])

    def test_required(self):
        for key in ("customer_id","fund_ref","data_item","data_phase","owner","source","frequency","validation_rule","source_ref","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_wtp_transition_data(d)

    def test_empty_string_rejected_for_required(self):
        with self.assertRaises(ValueError):
            store.save_wtp_transition_data({**BASE,"data_item":"   "})

    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_wtp_transition_data({**BASE,"customer_id":"unknown"})

    def test_data_phase_enum(self):
        with self.assertRaises(ValueError):
            store.save_wtp_transition_data({**BASE,"data_phase":"nope"})

    def test_optional_fields_none(self):
        r=store.save_wtp_transition_data({**BASE,"reconciliation":None,"data_quality_norm":None,"evidence":None,"continuity_agreement":None})
        for k in ("reconciliation","data_quality_norm","evidence","continuity_agreement"):
            self.assertIsNone(r[k])

    def test_versioning_and_append_only(self):
        store.save_wtp_transition_data(BASE)
        r2=store.save_wtp_transition_data({**BASE,"validation_rule":"Nieuwe regel"})
        self.assertEqual(r2["version"],2)
        rows=store.wtp_transition_data(customer_id="northstar",fund_ref="FUND-SYNTH-01")
        self.assertEqual(len(rows),2)
        import sqlite3
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE wtp_transition_data SET data_item='x' WHERE id=?",(r2["id"],))
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM wtp_transition_data WHERE id=?",(r2["id"],))

    def test_query_filters(self):
        store.save_wtp_transition_data(BASE)
        store.save_wtp_transition_data({**BASE,"data_phase":"na","data_item":"Eindrapportage (synthetisch)"})
        self.assertEqual(len(store.wtp_transition_data(data_phase="voor")),1)
        self.assertEqual(len(store.wtp_transition_data(data_phase="na")),1)

if __name__=="__main__":
    unittest.main()
