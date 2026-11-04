import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="fee-comp-")+ "/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",fund_ref="FUND-SYNTH-01",fee_type="aum",fee_name="AUM standaard",
    currency="EUR",accrual_frequency="monthly",invoice_frequency="quarterly",
    rate_bps=50,tier_from=0,tier_to=1000000,minimum_amount=100,minimum_currency="EUR",
    fixed_amount=None,fixed_currency=None,fixed_frequency=None,performance_fee_pct=None,
    hurdle_rate_pct=None,high_water_mark=None,discount_pct=None,side_letter_ref=None,
    indexation_basis=None,indexation_frequency=None,effective_from="2026-01-01",
    effective_to=None,source_ref="SYNTHETIC-SRC",rationale="ok")

class FeeComponents(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()

    def test_save_basic(self):
        r=store.save_fee_component(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["fee_type"],"aum")
        self.assertEqual(r["currency"],"EUR")

    def test_required(self):
        for key in ("customer_id","fund_ref","fee_type","fee_name","currency","accrual_frequency","invoice_frequency","source_ref","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_fee_component(d)

    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_fee_component({**BASE,"customer_id":"unknown"})

    def test_fee_type_enum(self):
        with self.assertRaises(ValueError):
            store.save_fee_component({**BASE,"fee_type":"nope"})

    def test_currency_enum(self):
        with self.assertRaises(ValueError):
            store.save_fee_component({**BASE,"currency":"XXX"})

    def test_accrual_frequency_enum(self):
        with self.assertRaises(ValueError):
            store.save_fee_component({**BASE,"accrual_frequency":"nope"})

    def test_invoice_frequency_enum(self):
        with self.assertRaises(ValueError):
            store.save_fee_component({**BASE,"invoice_frequency":"nope"})

    def test_performance_fee(self):
        r=store.save_fee_component({**BASE,"fee_type":"performance","fee_name":"Perf","performance_fee_pct":10,"hurdle_rate_pct":5,"high_water_mark":1})
        self.assertEqual(r["performance_fee_pct"],10.0)
        self.assertEqual(r["hurdle_rate_pct"],5.0)
        self.assertEqual(r["high_water_mark"],1)

    def test_discount_side_letter(self):
        r=store.save_fee_component({**BASE,"fee_type":"discount","fee_name":"Korting","discount_pct":2.5,"side_letter_ref":"SL-001"})
        self.assertEqual(r["discount_pct"],2.5)
        self.assertEqual(r["side_letter_ref"],"SL-001")

    def test_fixed_fee(self):
        r=store.save_fee_component({**BASE,"fee_type":"fixed","fee_name":"Vaste fee","fixed_amount":1000,"fixed_currency":"EUR","fixed_frequency":"annual"})
        self.assertEqual(r["fixed_amount"],1000.0)
        self.assertEqual(r["fixed_frequency"],"annual")

    def test_minimum(self):
        r=store.save_fee_component({**BASE,"fee_type":"minimum","fee_name":"Minimum","minimum_amount":500,"minimum_currency":"EUR"})
        self.assertEqual(r["minimum_amount"],500.0)

    def test_indexation(self):
        r=store.save_fee_component({**BASE,"fee_type":"indexation","fee_name":"Indexatie","indexation_basis":"CPI","indexation_frequency":"annual"})
        self.assertEqual(r["indexation_basis"],"CPI")

    def test_versioning_append_only(self):
        store.save_fee_component(BASE)
        r2=store.save_fee_component(BASE)
        self.assertEqual(r2["version"],2)
        rows=store.fee_components(customer_id="northstar",fund_ref="FUND-SYNTH-01")
        self.assertEqual(len(rows),2)
        # append-only triggers
        with store.connect() as db:
            with self.assertRaises(Exception):
                db.execute("UPDATE fee_components SET fee_name='x' WHERE customer_id='northstar'")
            with self.assertRaises(Exception):
                db.execute("DELETE FROM fee_components WHERE customer_id='northstar'")

    def test_export_shape(self):
        store.save_fee_component(BASE)
        e=store.fee_components_export(customer_id="northstar",fund_ref="FUND-SYNTH-01")
        self.assertIn("generated_at",e)
        self.assertIn("perimeter",e)
        self.assertIn("coverage",e)
        self.assertIn("rows",e)
        self.assertEqual(e["coverage"],1)
        self.assertEqual(e["perimeter"]["customer_id"],"northstar")
        self.assertEqual(e["perimeter"]["fund_ref"],"FUND-SYNTH-01")

if __name__=="__main__":
    unittest.main()
