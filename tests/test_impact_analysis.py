import os, sys, tempfile, json, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="imp-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",baseline_ref="base-1",scenario_ref="scn-1",
    domains={"fees":{},"esg":{}},comparison={"delta":1},
    calc_logic_version="domain-v1",policy_version="1",schema_version="1",source_ref="src-1")

class ImpactAnalysis(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()

    def test_save_basic(self):
        r=store.save_impact_analysis(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["baseline_ref"],"base-1")

    def test_required(self):
        for key in ("customer_id","baseline_ref","scenario_ref","domains","comparison","calc_logic_version","policy_version","schema_version","source_ref"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_impact_analysis(d)

    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_impact_analysis({**BASE,"customer_id":"unknown"})

    def test_append_only(self):
        store.save_impact_analysis(BASE)
        with store.connect() as db:
            with self.assertRaises(Exception):
                db.execute("UPDATE impact_analysis SET outcome='x'")
            with self.assertRaises(Exception):
                db.execute("DELETE FROM impact_analysis")

    def test_versioning(self):
        store.save_impact_analysis(BASE)
        r2=store.save_impact_analysis({**BASE,"comparison":{"delta":2}})
        self.assertEqual(r2["version"],2)

    def test_reproducibility(self):
        r1=store.save_impact_analysis(BASE)
        o1=json.loads(r1["outcome"])
        r2=store.save_impact_analysis(BASE)
        o2=json.loads(r2["outcome"])
        self.assertEqual(o1,o2)

    def test_export(self):
        store.save_impact_analysis(BASE)
        ex=store.impact_analysis_export(customer_id="northstar")
        self.assertEqual(ex["coverage"],1)
        self.assertIn("generated_at",ex)

    def test_list_filter(self):
        store.save_impact_analysis(BASE)
        store.save_impact_analysis({**BASE,"scenario_ref":"scn-2"})
        rows=store.impact_analyses(customer_id="northstar",scenario_ref="scn-2")
        self.assertEqual(len(rows),1)

if __name__=="__main__":
    unittest.main()
