import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

BASE=dict(subject_type="customer_config", subject_id="DEMO-CLIENT", subject_version=1,
          document_type="contract", document_date="2026-01-15",
          owner="Compliance (te bevestigen)", confidentiality="intern",
          retention_class="default_10y", storage_ref="dms://synthetic/DEMO-CLIENT/contract-v1",
          actor="demo.compliance", rationale="Bewijsreferentie registratie")

class DR(unittest.TestCase):
    def setUp(self): isolated_db()
    def test_create_reference(self):
        d=store.save_document_reference(dict(BASE))
        self.assertEqual(d["version"],1)
        self.assertEqual(d["document_type"],"contract")
        self.assertEqual(d["confidentiality"],"intern")
        self.assertEqual(d["retention_class"],"default_10y")
        self.assertTrue(d["created_at"])
    def test_version_bound_append_only(self):
        d=store.save_document_reference(dict(BASE))
        d2=store.save_document_reference({**BASE, "confidentiality":"vertrouwelijk", "rationale":"herziening"})
        self.assertEqual(d2["version"],2)
        self.assertEqual(d["id"],d2["id"])
        with store.connect() as db:
            vers=[r["version"] for r in db.execute("SELECT version FROM document_references WHERE id=?",(d["id"],)).fetchall()]
        self.assertEqual(sorted(vers),[1,2])
        latest=store.document_references(subject_id="DEMO-CLIENT")[-1]
        self.assertEqual(latest["confidentiality"],"vertrouwelijk")
    def test_no_update_no_delete(self):
        d=store.save_document_reference(dict(BASE))
        import sqlite3
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE document_references SET confidentiality='open' WHERE id=?",(d["id"],))
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM document_references WHERE id=?",(d["id"],))
    def test_invalid_enum_rejected(self):
        for bad in ("document_type","confidentiality","retention_class"):
            with self.assertRaises(ValueError):
                store.save_document_reference({**BASE, bad:"nope"})
    def test_missing_fields_rejected(self):
        for field in ("document_type","document_date","owner","confidentiality","retention_class","storage_ref","subject_type","subject_id","subject_version"):
            d=dict(BASE); d.pop(field)
            with self.assertRaises(ValueError):
                store.save_document_reference(d)
    def test_no_inline_content(self):
        # geen contractbestand of klantgegeven in git: inline inhoud of bestandspad wordt geweigerd.
        with self.assertRaises(ValueError):
            store.save_document_reference({**BASE, "content":"SECRET CONTRACT TEXT"})
        with self.assertRaises(ValueError):
            store.save_document_reference({**BASE, "file_path":"/tmp/contract.pdf"})
        with self.assertRaises(ValueError):
            store.save_document_reference({**BASE, "storage_ref":"file://local/contract.pdf"})
    def test_audited(self):
        d=store.save_document_reference(dict(BASE))
        rows=store.audit_log()
        self.assertTrue(any(r["entity_type"]=="document_reference" and r["entity_id"]==d["id"] for r in rows))
    def test_subject_version_binding(self):
        store.save_document_reference({**BASE, "subject_version":1})
        store.save_document_reference({**BASE, "subject_version":2, "storage_ref":"dms://synthetic/DEMO-CLIENT/contract-v2"})
        rows=store.document_references(subject_id="DEMO-CLIENT", subject_version=2)
        self.assertTrue(all(r["subject_version"]==2 for r in rows))
        self.assertEqual(len(rows),1)
    def test_positive_integer_version_required(self):
        with self.assertRaises(ValueError):
            store.save_document_reference({**BASE, "subject_version":"1"})

if __name__=="__main__":
    unittest.main()
