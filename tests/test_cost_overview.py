import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="cost-ov-")+ "/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",fund_ref="FUND-SYNTH-01",cost_type="direct_fee",source_ref="SYNTHETIC-SRC",
    recipient="Custodian BV",period_start="2026-01-01",period_end="2026-03-31",perimeter="client",
    amount=1234.56,currency="EUR",rationale="ok")

class CostOverview(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()

    def test_save_basic(self):
        r=store.save_cost_overview(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["cost_type"],"direct_fee")
        self.assertEqual(r["currency"],"EUR")

    def test_required(self):
        for key in ("customer_id","fund_ref","cost_type","source_ref","recipient","period_start","period_end","perimeter","amount","currency","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_cost_overview(d)

    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_cost_overview({**BASE,"customer_id":"unknown"})

    def test_cost_type_enum(self):
        with self.assertRaises(ValueError):
            store.save_cost_overview({**BASE,"cost_type":"nope"})

    def test_currency_enum(self):
        with self.assertRaises(ValueError):
            store.save_cost_overview({**BASE,"currency":"XXX"})

    def test_perimeter_enum(self):
        with self.assertRaises(ValueError):
            store.save_cost_overview({**BASE,"perimeter":"nope"})

    def test_performance_fee(self):
        r=store.save_cost_overview({**BASE,"cost_type":"performance_fee","amount":5000})
        self.assertEqual(r["cost_type"],"performance_fee")

    def test_other_agreed(self):
        r=store.save_cost_overview({**BASE,"cost_type":"other_agreed","recipient":"Advisor"})
        self.assertEqual(r["cost_type"],"other_agreed")

    def test_allocation(self):
        r=store.save_cost_overview({**BASE,"mandate_ref":"M-1","product_ref":"P-1","allocation_basis":"AUM","coverage_pct":100})
        self.assertEqual(r["mandate_ref"],"M-1")
        self.assertEqual(r["product_ref"],"P-1")
        self.assertEqual(r["coverage_pct"],100.0)

    def test_append_only(self):
        store.save_cost_overview(BASE)
        with store.connect() as db:
            with self.assertRaises(Exception):
                db.execute("UPDATE cost_overview SET amount=999")
            with self.assertRaises(Exception):
                db.execute("DELETE FROM cost_overview")

    def test_versioning(self):
        store.save_cost_overview(BASE)
        r2=store.save_cost_overview({**BASE,"amount":999})
        self.assertEqual(r2["version"],2)

    def test_export(self):
        store.save_cost_overview(BASE)
        ex=store.cost_overview_export(customer_id="northstar")
        self.assertEqual(ex["coverage"],1)
        self.assertIn("perimeter",ex)
        self.assertIn("generated_at",ex)

    def test_list_filter(self):
        store.save_cost_overview(BASE)
        store.save_cost_overview({**BASE,"cost_type":"performance_fee","period_start":"2026-04-01","period_end":"2026-06-30"})
        rows=store.cost_overview(customer_id="northstar",cost_type="performance_fee")
        self.assertEqual(len(rows),1)

if __name__=="__main__":
    unittest.main()
