import os, sys, tempfile, json, unittest, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="ps-")+ "/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",export_id="exp-001",checksum="abc123",snapshot_version="snap-1",
    schema_version="1.0",mapping_version="1.0",actor="demo.client-service",published_at="2026-01-01T00:00:00",
    target="partner-a",receipt_status="received",processing_status="processed",source_ref="src-1")

class PublicationStatus(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()

    def test_save_basic(self):
        r=store.save_publication_status(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["export_id"],"exp-001")

    def test_required(self):
        for key in store.PUBLICATION_STATUS_REQUIRED:
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_publication_status(d)

    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_publication_status({**BASE,"customer_id":"unknown"})

    def test_append_only(self):
        store.save_publication_status(BASE)
        with store.connect() as db:
            with self.assertRaises(Exception):
                db.execute("UPDATE publication_status_versions SET target='x'")
            with self.assertRaises(Exception):
                db.execute("DELETE FROM publication_status_versions")

    def test_versioning(self):
        store.save_publication_status(BASE)
        r2=store.save_publication_status({**BASE,"receipt_status":"duplicate"})
        self.assertEqual(r2["version"],2)

    def test_list_filter(self):
        store.save_publication_status(BASE)
        store.save_publication_status({**BASE,"target":"partner-b"})
        rows=store.publication_statuses(customer_id="northstar",target="partner-b")
        self.assertEqual(len(rows),1)

    def test_export(self):
        store.save_publication_status(BASE)
        ex=store.publication_status_export(customer_id="northstar")
        self.assertEqual(ex["coverage"],1)

if __name__=="__main__":
    unittest.main()