import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="wtp-risk-")+ "/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",fund_ref="FUND-SYNTH-01",risk_category="data",
    risk_description="Ontbrekende data-interface",mitigation="Aanvullende extractie",
    change_impact="mandaat en reporting",source_ref="SYNTHETIC-SRC",rationale="ok")

class WTPRisks(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()

    def test_save_basic(self):
        r=store.save_wtp_risk(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["risk_category"],"data")

    def test_required(self):
        for key in ("customer_id","fund_ref","risk_category","risk_description","mitigation","change_impact","source_ref","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_wtp_risk(d)

    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_wtp_risk({**BASE,"customer_id":"unknown"})

    def test_risk_category_enum(self):
        with self.assertRaises(ValueError):
            store.save_wtp_risk({**BASE,"risk_category":"nope"})

    def test_evidence_status_enum(self):
        with self.assertRaises(ValueError):
            store.save_wtp_risk({**BASE,"evidence_status":"nope"})

    def test_versioning_append_only(self):
        store.save_wtp_risk(BASE)
        r2=store.save_wtp_risk({**BASE,"risk_description":"Nieuw risico"})
        self.assertEqual(r2["version"],2)
        rows=store.wtp_risks(customer_id="northstar",fund_ref="FUND-SYNTH-01")
        self.assertEqual(len(rows),2)
        # append-only triggers
        with store.connect() as db:
            with self.assertRaises(Exception):
                db.execute("UPDATE wtp_risks SET risk_description='x' WHERE customer_id='northstar'")
            with self.assertRaises(Exception):
                db.execute("DELETE FROM wtp_risks WHERE customer_id='northstar'")

if __name__=="__main__":
    unittest.main()
