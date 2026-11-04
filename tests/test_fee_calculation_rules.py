import os, sys, tempfile, unittest
from pathlib import Path
from decimal import Decimal
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="feerule-")+ "/t.db")
from app import store, domain

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",fund_ref="FUND-SYNTH-01",rule_name="Standaard",
    base="aum",measurement_period="quarterly",valuation_input="eod_nav",
    fx_basis="EUR",rounding_mode="half_up",cap_amount=None,floor_amount=None,
    edge_case="none",effective_from="2026-01-01",effective_to=None,
    source_ref="SYNTHETIC-SRC",rationale="ok")

class FeeCalcRulesStore(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()

    def test_save_basic(self):
        r=store.save_fee_calculation_rule(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["base"],"aum")

    def test_required(self):
        for key in ("customer_id","fund_ref","rule_name","base","measurement_period","valuation_input","rounding_mode","source_ref","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_fee_calculation_rule(d)

    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_fee_calculation_rule({**BASE,"customer_id":"unknown"})

    def test_base_enum(self):
        with self.assertRaises(ValueError):
            store.save_fee_calculation_rule({**BASE,"base":"nope"})

    def test_measurement_period_enum(self):
        with self.assertRaises(ValueError):
            store.save_fee_calculation_rule({**BASE,"measurement_period":"nope"})

    def test_valuation_input_enum(self):
        with self.assertRaises(ValueError):
            store.save_fee_calculation_rule({**BASE,"valuation_input":"nope"})

    def test_rounding_mode_enum(self):
        with self.assertRaises(ValueError):
            store.save_fee_calculation_rule({**BASE,"rounding_mode":"nope"})

    def test_versioning(self):
        store.save_fee_calculation_rule(BASE)
        r2=store.save_fee_calculation_rule({**BASE,"rationale":"v2"})
        self.assertEqual(r2["version"],2)

    def test_append_only(self):
        store.save_fee_calculation_rule(BASE)
        with store.connect() as db:
            with self.assertRaises(Exception):
                db.execute("UPDATE fee_calculation_rules SET rationale='x'")
            with self.assertRaises(Exception):
                db.execute("DELETE FROM fee_calculation_rules WHERE id IS NOT NULL")

    def test_export_shape(self):
        store.save_fee_calculation_rule(BASE)
        ex=store.fee_calculation_rules_export(customer_id="northstar")
        self.assertIn("generated_at",ex)
        self.assertIn("perimeter",ex)
        self.assertIn("coverage",ex)
        self.assertIn("rows",ex)
        self.assertEqual(ex["coverage"],1)

class DomainFee(unittest.TestCase):
    def test_round_money_modes(self):
        self.assertEqual(domain.round_money("2.345",2,"half_up"), Decimal("2.35"))
        self.assertEqual(domain.round_money("2.345",2,"half_even"), Decimal("2.34"))
        self.assertEqual(domain.round_money("2.341",2,"floor"), Decimal("2.34"))
        self.assertEqual(domain.round_money("2.341",2,"ceil"), Decimal("2.35"))
        with self.assertRaises(ValueError):
            domain.round_money(1,2,"nope")

    def test_fx_convert(self):
        self.assertEqual(domain.fx_convert(100,"EUR","USD",1.1), Decimal("110.0"))
        self.assertEqual(domain.fx_convert(100,"EUR","EUR",1.1), Decimal("100"))

    def test_apply_cap_floor(self):
        self.assertEqual(domain.apply_cap_floor(50,cap=40,floor=10), Decimal("40"))
        self.assertEqual(domain.apply_cap_floor(5,cap=40,floor=10), Decimal("10"))

    def test_tiered_fee(self):
        tiers=[(0,1000,10),(1000,None,5)]
        self.assertEqual(domain.tiered_fee(500,[]), Decimal("0"))
        self.assertEqual(domain.tiered_fee(1500,tiers), Decimal("1000")*Decimal("10")/Decimal("10000")+Decimal("500")*Decimal("5")/Decimal("10000"))
        self.assertEqual(domain.tiered_fee(1200,tiers), Decimal("1000")*Decimal("10")/Decimal("10000")+Decimal("200")*Decimal("5")/Decimal("10000"))

    def test_minimum_fee(self):
        self.assertEqual(domain.minimum_fee(5,10), Decimal("10"))

    def test_performance_fee(self):
        self.assertEqual(domain.performance_fee(100,50,high_water_mark=0,performance_fee_pct=20), Decimal("100")*Decimal("0.5")*Decimal("0.2"))
        self.assertEqual(domain.performance_fee(50,0,high_water_mark=60,performance_fee_pct=20), Decimal("0"))

    def test_calculate_fee(self):
        r=domain.calculate_fee(1000,50,minimum=10,cap=100,floor=1,fx_rate=1.1,from_ccy="EUR",to_ccy="USD",rounding="half_up",decimals=2)
        self.assertTrue(isinstance(r,Decimal))