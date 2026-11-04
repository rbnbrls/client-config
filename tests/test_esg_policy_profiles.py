import os, sys, tempfile, sqlite3, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="esg-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

MANDATE_BASE=dict(customer_id="northstar",fund_ref="SYNTHETIC-FUND-001",subject_type="mandate",
    subject_id="SYNTHETIC-MANDATE-001",policy_framework="MVB/ESG fondsbeleid 2026",
    goals="Klimaatneutrale portefeuille in 2045",priority="sustainability",
    asset_class_scope="listed_equity,corporate_bonds",effective_from="2026-01-01",
    source_ref="SYNTHETIC-POLICY-DOC-001",rationale="beleid voorbeeld")
FUND_BASE=dict(MANDATE_BASE,subject_type="fund",subject_id=None)

class ESG001(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()
    # --- basis: per klant/fonds/mandaat geldend MVB/ESG-beleid, doelen, prioriteit, asset-class scope, versie, bronbewijs
    def test_save_basic(self):
        r=store.save_esg_policy_profile({**MANDATE_BASE})
        self.assertEqual(r["version"],1)
        self.assertEqual(r["priority"],"sustainability")
        self.assertEqual(r["asset_class_scope"],"listed_equity,corporate_bonds")
        self.assertTrue(r["source_ref"])
    def test_required_fields(self):
        for key in ("customer_id","fund_ref","subject_type","policy_framework","goals","priority",
                    "asset_class_scope","effective_from","source_ref","rationale"):
            with self.assertRaises(ValueError):
                store.save_esg_policy_profile({**MANDATE_BASE,key:None})
    def test_unknown_customer_rejected(self):
        with self.assertRaises(ValueError):
            store.save_esg_policy_profile({**MANDATE_BASE,"customer_id":"unknown"})
    def test_subject_type_and_priority_enum(self):
        with self.assertRaises(ValueError):
            store.save_esg_policy_profile({**MANDATE_BASE,"subject_type":"onbekend"})
        with self.assertRaises(ValueError):
            store.save_esg_policy_profile({**MANDATE_BASE,"priority":"glamour"})
    def test_invalid_or_reversed_validity(self):
        with self.assertRaises(ValueError):
            store.save_esg_policy_profile({**MANDATE_BASE,"effective_from":"01-01-2026"})
        with self.assertRaises(ValueError):
            store.save_esg_policy_profile({**MANDATE_BASE,"effective_to":"2025-01-01"})
    # --- validatienotitie P3: het verlopen IMVB-convenant is geen zelfstandige actuele wettelijke verplichting;
    # de IMVB-invulling leeft per klant/fonds in het profiel met bronbewijs naar klantaafspraak/fondsbeleid.
    def test_seed_has_no_standalone_imvb_covenant_obligation(self):
        with store.connect() as db:
            rows=db.execute("SELECT title,source_ref FROM policy_controls").fetchall()
        covenant=[r for r in rows if "convenant" in (r["title"]+" "+(r["source_ref"] or "")).lower()]
        self.assertEqual(covenant,[])
    def test_imvb_invulling_per_klant_met_bron(self):
        r=store.save_esg_policy_profile({**MANDATE_BASE,
            "imvb_diligence":"IMVB-invulling vastgelegd in klantcontract SYNTHETIC-KLANT-BIJLAGE-5",
            "oeso_ungp_diligence":"OESO/UNGP due diligence per klantafspraak toegekend"})
        self.assertIn("klantcontract",r["imvb_diligence"])
        self.assertIn("oeso",r["oeso_ungp_diligence"].lower())
    # --- versiering: append-only, geen overwrite
    def test_versioned_no_overwrite(self):
        store.save_esg_policy_profile({**MANDATE_BASE})
        store.save_esg_policy_profile({**MANDATE_BASE,"priority":"risk","asset_class_scope":"listed_equity",
            "effective_from":"2027-01-01","rationale":"prioriteit verschoven"})
        with store.connect() as db:
            vers=[r["version"] for r in db.execute(
                "SELECT version FROM esg_policy_profiles WHERE customer_id=? AND fund_ref=?",
                ("northstar","SYNTHETIC-FUND-001")).fetchall()]
        self.assertEqual(sorted(vers),[1,2])
    def test_append_only_update_delete_blocked(self):
        store.save_esg_policy_profile({**MANDATE_BASE})
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE esg_policy_profiles SET priority='return'")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM esg_policy_profiles WHERE customer_id=?",("northstar",))
    # --- zichtbaar en bewijsbaar bij manager onboarding / jaarlijkse review
    def test_in_force_mandate_specific_beats_fund_default(self):
        store.save_esg_policy_profile({**FUND_BASE})
        store.save_esg_policy_profile({**MANDATE_BASE})
        r=store.esg_policy_profile_in_force("northstar","SYNTHETIC-FUND-001",
            subject_type="mandate",subject_id="SYNTHETIC-MANDATE-001",valid_at="2026-03-01")
        self.assertEqual(r["resolved_from"],"mandate_specific")
        self.assertEqual(r["evidence"]["source_ref"],"SYNTHETIC-POLICY-DOC-001")
        fund_res=store.esg_policy_profile_in_force("northstar","SYNTHETIC-FUND-001",valid_at="2026-03-01")
        self.assertEqual(fund_res["resolved_from"],"fund_default")
    def test_in_force_honours_effective_window(self):
        store.save_esg_policy_profile({**MANDATE_BASE})
        with self.assertRaises(ValueError):
            store.esg_policy_profile_in_force("northstar","SYNTHETIC-FUND-001",
                subject_type="mandate",subject_id="SYNTHETIC-MANDATE-001",valid_at="2025-12-31")
    def test_in_force_known_at_in_past_finds_nothing(self):
        store.save_esg_policy_profile({**MANDATE_BASE})
        with self.assertRaises(ValueError):
            store.esg_policy_profile_in_force("northstar","SYNTHETIC-FUND-001",
                subject_type="mandate",subject_id="SYNTHETIC-MANDATE-001",
                valid_at="2026-03-01",known_at="2020-01-01T00:00:00Z")
    def test_query_customer_filter(self):
        store.save_esg_policy_profile({**MANDATE_BASE})
        with store.connect() as db:
            db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
                ("meridian","Meridian","asset_manager","NL","institutional",store.now()))
        store.save_esg_policy_profile({**MANDATE_BASE,"customer_id":"meridian"})
        rows=store.esg_policy_profiles(customer_id="northstar")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["customer_id"],"northstar")
    # --- uitzonderingen: rationale, goedkeurder en einddatum verplicht
    def save_profile(self):
        return store.save_esg_policy_profile({**MANDATE_BASE})
    def test_exception_requires_rationale_approver_end_date(self):
        p=self.save_profile()
        for key in ("description","rationale","approver","end_date"):
            d=dict(customer_id="northstar",profile_id=p["id"],description="exclusie fossiel waterstof",
                   rationale="beoordelingsfout bij ratingbron",approver="Compliance",end_date="2026-12-31")
            d[key]=None
            with self.assertRaises(ValueError):
                store.save_esg_policy_exception(d)
    def test_exception_end_date_must_be_iso_date(self):
        p=self.save_profile()
        with self.assertRaises(ValueError):
            store.save_esg_policy_exception(dict(customer_id="northstar",profile_id=p["id"],
                description="x",rationale="y",approver="Compliance",end_date="geen datum"))
    def test_exception_must_reference_existing_profile(self):
        p=self.save_profile()
        with self.assertRaises(ValueError):
            store.save_esg_policy_exception(dict(customer_id="northstar",profile_id="onbekend",
                description="x",rationale="y",approver="Compliance",end_date="2026-12-31"))
    def test_exception_append_only_and_expiry_by_date(self):
        p=self.save_profile()
        e=store.save_esg_policy_exception(dict(customer_id="northstar",profile_id=p["id"],
            description="exclusie fossiel waterstof",rationale="beoordelingsfout bij ratingbron",
            approver="Compliance",end_date="2026-12-31",effective_from="2026-01-01"))
        self.assertEqual(e["version"],1)
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM esg_policy_exceptions")
        expired=store.esg_policy_exceptions(valid_at="2027-01-02",customer_id="northstar")
        self.assertEqual(expired[0]["validity_status"],"expired")
        active=store.esg_policy_exceptions(valid_at="2026-06-30",customer_id="northstar")
        self.assertEqual(active[0]["validity_status"],"active")
    # --- beleidswijziging laat zien welke managers/mandaten en rapportageprofielen geraakt worden
    def add_requirements(self):
        with store.connect() as db:
            db.execute("INSERT INTO client_requirements(id,version,customer_id,category,title,requirement,source_ref,config_path,expected_value,frequency,effective_date,review_date,created_by,created_at,rationale) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("req-report",1,"northstar","reporting","Kwartaalrapportage SFDR-indicatoren",
                 "SFDR-indicatoren per kwartaal","SYNTHETIC-SRC","reporting.frequency","quarterly",
                 "yearly","2026-01-01","2027-01-01","demo.client-service","2026-01-01T00:00:00Z","verwant vereiste"))
    def test_change_impact_lists_affected_mandates_and_reporting(self):
        store.save_esg_policy_profile({**MANDATE_BASE})
        # FUND-002 profiel wijkt niet af van de voorgestelde klantbeleidswaarden → niet geraakt.
        store.save_esg_policy_profile({**FUND_BASE,"fund_ref":"SYNTHETIC-FUND-002","priority":"risk","asset_class_scope":"listed_equity"})
        self.add_requirements()
        impact=store.esg_policy_change_impact(dict(customer_id="northstar",priority="risk",
            asset_class_scope="listed_equity",policy_framework="MVB/ESG fondsbeleid 2026"))
        mandates={(m["fund_ref"],m["subject_id"]) for m in impact["affected_managers_mandates"]}
        self.assertIn(("SYNTHETIC-FUND-001","SYNTHETIC-MANDATE-001"),mandates)
        self.assertNotIn(("SYNTHETIC-FUND-002",None),mandates)
        affected={(a["fund_ref"],a["subject_type"]) for a in impact["affected_profiles"]}
        self.assertIn(("SYNTHETIC-FUND-001","mandate"),affected)
        self.assertNotIn(("SYNTHETIC-FUND-002","fund"),affected)
        cats={r["category"] for r in impact["affected_reporting_requirements"]}
        self.assertIn("reporting",cats)
    def test_change_impact_requires_known_customer(self):
        with self.assertRaises(ValueError):
            store.esg_policy_change_impact(dict(customer_id="unknown",priority="risk"))

if __name__=="__main__":
    unittest.main()
