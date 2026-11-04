import os, sys, tempfile, json, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="scn-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",scenario_name="Scenario A",
    snapshot={"a":1},inputs={"x":2},
    calc_logic_version="domain-v1",policy_version="1",schema_version="1")

class ScenarioSnapshot(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()

    def test_save_basic(self):
        r=store.save_scenario_snapshot(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["scenario_name"],"Scenario A")

    def test_required(self):
        for key in ("customer_id","scenario_name","snapshot","inputs","calc_logic_version","policy_version","schema_version"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_scenario_snapshot(d)

    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_scenario_snapshot({**BASE,"customer_id":"unknown"})

    def test_append_only(self):
        store.save_scenario_snapshot(BASE)
        with store.connect() as db:
            with self.assertRaises(Exception):
                db.execute("UPDATE scenario_snapshots SET outcome='x'")
            with self.assertRaises(Exception):
                db.execute("DELETE FROM scenario_snapshots")

    def test_versioning(self):
        store.save_scenario_snapshot(BASE)
        r2=store.save_scenario_snapshot({**BASE,"inputs":{"x":3}})
        self.assertEqual(r2["version"],2)

    def test_reproducibility(self):
        r1=store.save_scenario_snapshot(BASE)
        # recompute outcome identical for same snapshot+inputs+versions
        import json
        o1=json.loads(r1["outcome"])
        r2=store.save_scenario_snapshot(BASE)
        o2=json.loads(r2["outcome"])
        self.assertEqual(o1,o2)

    def test_export(self):
        store.save_scenario_snapshot(BASE)
        ex=store.scenario_snapshot_export(customer_id="northstar")
        self.assertEqual(ex["coverage"],1)
        self.assertIn("generated_at",ex)

    def test_list_filter(self):
        store.save_scenario_snapshot(BASE)
        store.save_scenario_snapshot({**BASE,"scenario_name":"B"})
        rows=store.scenario_snapshots(customer_id="northstar",scenario_name="B")
        self.assertEqual(len(rows),1)

if __name__=="__main__":
    unittest.main()