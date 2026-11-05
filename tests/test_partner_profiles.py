import os, sys, tempfile, json, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="pp-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",partner_id="partner-a",partner_name="Partner A",
    format="json",mapping={"customer":"customer_id","services":"service_catalog"},
    validation={"required":["customer_id"],"types":{"customer_id":"str"}},
    classification="partner-confidential",privacy_filter="pii-masked",
    schema_version="1.0",source_ref="src-1")

class PartnerProfiles(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()

    def test_save_basic(self):
        r=store.save_partner_profile(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["partner_id"],"partner-a")
        self.assertEqual(r["format"],"json")

    def test_required(self):
        for key in store.PARTNER_PROFILE_REQUIRED:
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_partner_profile(d)

    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_partner_profile({**BASE,"customer_id":"unknown"})

    def test_mapping_validation_type_checks(self):
        with self.assertRaises(ValueError):
            store.save_partner_profile({**BASE,"mapping":123})
        with self.assertRaises(ValueError):
            store.save_partner_profile({**BASE,"validation":42})

    def test_classification_privacy_nonempty(self):
        for field in ("classification","privacy_filter"):
            d=dict(BASE); d[field]="   "
            with self.assertRaises(ValueError):
                store.save_partner_profile(d)

    def test_append_only(self):
        store.save_partner_profile(BASE)
        with store.connect() as db:
            with self.assertRaises(Exception):
                db.execute("UPDATE partner_profiles_versions SET partner_name='x'")
            with self.assertRaises(Exception):
                db.execute("DELETE FROM partner_profiles_versions")

    def test_versioning(self):
        store.save_partner_profile(BASE)
        r2=store.save_partner_profile({**BASE,"validation":{"required":["customer_id"],"types":{"customer_id":"str"},"v":2}})
        self.assertEqual(r2["version"],2)

    def test_reproducibility(self):
        r1=store.save_partner_profile(BASE)
        o1=json.loads(r1["mapping"]) if False else r1["mapping"]
        r2=store.save_partner_profile(BASE)
        self.assertEqual(r1["mapping"],r2["mapping"])
        self.assertEqual(r1["validation"],r2["validation"])
        self.assertEqual(r1["classification"],r2["classification"])
        self.assertEqual(r1["privacy_filter"],r2["privacy_filter"])

    def test_list_filter(self):
        store.save_partner_profile(BASE)
        store.save_partner_profile({**BASE,"format":"csv"})
        rows=store.partner_profiles(customer_id="northstar",format="csv")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["format"],"csv")

    def test_export(self):
        store.save_partner_profile(BASE)
        ex=store.partner_profile_export(customer_id="northstar")
        self.assertEqual(ex["coverage"],1)
        self.assertIn("generated_at",ex)

    def test_contract_test_field(self):
        r=store.save_partner_profile({**BASE,"contract_test":{"schema":"1.0","checks":["mapping_keys"]}})
        self.assertIn("contract_test",r)
        import json as _j
        self.assertEqual(_j.loads(r["contract_test"])["schema"],"1.0")

if __name__=="__main__":
    unittest.main()
