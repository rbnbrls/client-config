import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="feesim-")+ "/t.db")
from app import store, domain

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",fund_ref="FUND-SYNTH-01",scenario_name="Scenario A",level="total",
    source_ref="SYNTHETIC-SRC",rationale="ok")

class FeeSimulation(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()

    def test_save_basic(self):
        r=store.save_fee_simulation(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["level"],"total")

    def test_required(self):
        for key in ("customer_id","fund_ref","scenario_name","level","source_ref","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_fee_simulation(d)

    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_fee_simulation({**BASE,"customer_id":"unknown"})

    def test_level_enum(self):
        with self.assertRaises(ValueError):
            store.save_fee_simulation({**BASE,"level":"nope"})

    def test_append_only(self):
        store.save_fee_simulation(BASE)
        with store.connect() as db:
            with self.assertRaises(Exception):
                db.execute("UPDATE fee_simulation SET baseline_amount=999")
            with self.assertRaises(Exception):
                db.execute("DELETE FROM fee_simulation")

    def test_versioning(self):
        store.save_fee_simulation(BASE)
        r2=store.save_fee_simulation({**BASE,"baseline_amount":1000})
        self.assertEqual(r2["version"],2)

    def test_export(self):
        store.save_fee_simulation(BASE)
        ex=store.fee_simulation_export(customer_id="northstar")
        self.assertEqual(ex["coverage"],1)
        self.assertIn("perimeter",ex)
        self.assertIn("generated_at",ex)

    def test_list_filter(self):
        store.save_fee_simulation(BASE)
        store.save_fee_simulation({**BASE,"level":"manager","scenario_name":"B"})
        rows=store.fee_simulation(customer_id="northstar",level="manager")
        self.assertEqual(len(rows),1)

    def test_shared_domain_function(self):
        prod=domain.calculate_fee(1000000, 20)
        twin=domain.calculate_fee(1000000, 20)
        self.assertEqual(prod, twin)

if __name__=="__main__":
    unittest.main()
