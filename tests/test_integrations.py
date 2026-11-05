import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="int-")+ "/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",source="FactSet",direction="inbound",frequency="daily",
    data_owner="data.owner",contract="contract-v1",privacy_classification="internal",
    reconciliation="manual_review",actor="demo.client-service",source_ref="src-1")

class Integrations(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()

    def test_save_basic(self):
        r=store.save_integration(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["source"],"FactSet")

    def test_required(self):
        for key in store.INTEGRATION_REQUIRED:
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_integration(d)

    def test_direction_invalid(self):
        with self.assertRaises(ValueError):
            store.save_integration({**BASE,"direction":"sideways"})

    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_integration({**BASE,"customer_id":"unknown"})

    def test_append_only(self):
        store.save_integration(BASE)
        with store.connect() as db:
            with self.assertRaises(Exception):
                db.execute("UPDATE integration_versions SET source='x'")
            with self.assertRaises(Exception):
                db.execute("DELETE FROM integration_versions")

    def test_delivery_append_only(self):
        store.save_integration(BASE)
        row=store.integrations(customer_id="northstar")[0]
        store.record_integration_delivery(dict(customer_id="northstar",integration_id=row["id"],payload_checksum="abc",delivery_status="delivered",actor="demo",source_ref="src"))
        with store.connect() as db:
            with self.assertRaises(Exception):
                db.execute("UPDATE integration_deliveries SET delivery_status='x'")
            with self.assertRaises(Exception):
                db.execute("DELETE FROM integration_deliveries")

    def test_versioning(self):
        store.save_integration(BASE)
        r2=store.save_integration({**BASE,"frequency":"weekly"})
        self.assertEqual(r2["version"],2)

    def test_list_filter(self):
        store.save_integration(BASE)
        store.save_integration({**BASE,"source":"Power BI"})
        rows=store.integrations(customer_id="northstar",source="Power BI")
        self.assertEqual(len(rows),1)

    def test_delivery_statuses(self):
        store.save_integration(BASE)
        row=store.integrations(customer_id="northstar")[0]
        for st in ("delivered","failed","duplicate"):
            store.record_integration_delivery(dict(customer_id="northstar",integration_id=row["id"],payload_checksum="abc",delivery_status=st,actor="demo",source_ref="src"))
        rows=store.integration_deliveries(customer_id="northstar",delivery_status="failed")
        self.assertEqual(len(rows),1)
        with self.assertRaises(ValueError):
            store.record_integration_delivery(dict(customer_id="northstar",integration_id=row["id"],payload_checksum="abc",delivery_status="bogus",actor="demo",source_ref="src"))

    def test_export(self):
        store.save_integration(BASE)
        ex=store.integration_export(customer_id="northstar")
        self.assertEqual(ex["coverage"],1)

if __name__=="__main__":
    unittest.main()
