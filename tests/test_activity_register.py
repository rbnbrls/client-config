import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="ar-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

BASE=dict(customer_id="northstar",activity_code="OUT-001-FID",
    title="Fiduciair vermogensbeheer",description="Beleidsbepaling en risicomanagement",
    boundaries="Geen afgeleide producten; advisory-delegatie",
    services='["FIDUCIARY","RISK"]',fund_mandate_ref="Strategisch mandaat",
    criticality="hoog",materiality="materieel",owner="demo.client-service",
    contract_start="2026-01-01",source_ref="SYNTHETIC-CONTRACT-001",rationale="r",
    effective_from="2026-01-01")

class AR(unittest.TestCase):
    def setUp(self): isolated_db()
    def test_register_activity(self):
        a=store.save_activity({**BASE})
        self.assertEqual(a["activity_code"],"OUT-001-FID")
        self.assertEqual(a["version"],1)
        self.assertEqual(a["contract_start"],"2026-01-01")
    def test_required_fields(self):
        for key in ("title","owner","contract_start","boundaries","services","fund_mandate_ref","criticality","materiality"):
            with self.assertRaises(ValueError):
                store.save_activity({**BASE, key:None if key!="services" else None})
    def test_versioned_no_overwrite(self):
        a=store.save_activity({**BASE})
        store.save_activity({**a,"owner":"demo.risk","rationale":"correctie"})
        with store.connect() as db:
            vers=[r["version"] for r in db.execute("SELECT version FROM activity_register WHERE id=?",(a["id"],)).fetchall()]
        self.assertEqual(sorted(vers),[1,2])
        latest=store.activities(customer_id="northstar")
        self.assertEqual([r for r in latest if r["id"]==a["id"]][0]["owner"],"demo.risk")
    def test_append_only_delete_blocked(self):
        import sqlite3
        a=store.save_activity({**BASE})
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM activity_register WHERE id=?",(a["id"],))
    def test_contract_end_after_start(self):
        with self.assertRaises(ValueError):
            store.save_activity({**BASE, "contract_end":"2025-01-01"})
    def test_chain_missing_contract_fields(self):
        a=store.save_activity({**BASE})  # geen contract_end
        chain=store.activity_chain(customer_id="northstar",activity_id=a["id"])
        self.assertEqual(chain["activity"]["id"],a["id"])
        self.assertIn("contract_end",chain["missing_contract_fields"])
        self.assertIn("FIDUCIARY",chain["services"])
    def test_chain_complete(self):
        a=store.save_activity({**BASE,"contract_end":"2027-12-31"})
        chain=store.activity_chain(customer_id="northstar",activity_id=a["id"])
        self.assertEqual(chain["missing_contract_fields"],[])
        self.assertEqual(chain["activity"]["fund_mandate_ref"],"Strategisch mandaat")
    def test_chain_unknown_activity(self):
        with self.assertRaises(ValueError):
            store.activity_chain(customer_id="northstar",activity_id="onbekend")
    def test_valid_time_filter(self):
        a=store.save_activity({**BASE,"effective_from":"2026-06-01"})
        rows=store.activities(customer_id="northstar",valid_at="2026-05-01",known_at="2099-01-01T00:00:00Z")
        self.assertFalse(any(r["id"]==a["id"] for r in rows))
        rows=store.activities(customer_id="northstar",valid_at="2026-07-01",known_at="2099-01-01T00:00:00Z")
        self.assertTrue(any(r["id"]==a["id"] for r in rows))
    def test_review_status_signal(self):
        a=store.save_activity({**BASE})
        chain=store.activity_chain(customer_id="northstar",activity_id=a["id"])
        self.assertEqual(chain["review_status"],"pending")  # open gate: Compliance/Legal-validatie

if __name__=="__main__": unittest.main()
