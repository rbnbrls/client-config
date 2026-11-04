import os, sys, tempfile, sqlite3, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="wtp-raci-")+"/t.db")
from app import store

def isolated_db():
    h,p=tempfile.mkstemp(suffix=".db"); os.close(h); os.unlink(p)
    store.DB_PATH=Path(p); store.init()

def seed_customer():
    with store.connect() as db:
        db.execute("INSERT OR IGNORE INTO customers(id,name,kind,jurisdiction,classification,created_at) VALUES(?,?,?,?,?,?)",
            ("northstar","Northstar","pension","NL","institutional",store.now()))

BASE=dict(customer_id="northstar",fund_ref="FUND-SYNTH-01",party_role="fiduciair",
    party_name="Fiduciair manager (synthetisch)",task="Beheeroverdracht en datalevering",
    input="Fondsregeling, deelnemersdata",output="Transitieplan, rapportage",
    handoff="PUO",dependency="Fondsbesluit go-live",escalation="Client lead -> Risk",
    critical_milestone="2026-10-18",evidence_status="in behandeling",
    source_ref="SYNTHETIC-SRC",rationale="ok")

class WTPRaciDependencies(unittest.TestCase):
    def setUp(self):
        isolated_db(); seed_customer()

    def test_save_basic(self):
        r=store.save_wtp_raci_dependency(BASE)
        self.assertEqual(r["version"],1)
        self.assertEqual(r["party_role"],"fiduciair")
        self.assertEqual(r["party_name"],BASE["party_name"])
        self.assertEqual(r["task"],BASE["task"])
        self.assertEqual(r["handoff"],"PUO")
        self.assertEqual(r["dependency"],BASE["dependency"])
        self.assertEqual(r["critical_milestone"],"2026-10-18")

    def test_required(self):
        for key in ("customer_id","fund_ref","party_role","party_name","task","source_ref","rationale"):
            d=dict(BASE); d[key]=None
            with self.assertRaises(ValueError):
                store.save_wtp_raci_dependency(d)

    def test_empty_string_rejected_for_required(self):
        with self.assertRaises(ValueError):
            store.save_wtp_raci_dependency({**BASE,"task":"   "})

    def test_unknown_customer(self):
        with self.assertRaises(ValueError):
            store.save_wtp_raci_dependency({**BASE,"customer_id":"unknown"})

    def test_party_role_enum(self):
        with self.assertRaises(ValueError):
            store.save_wtp_raci_dependency({**BASE,"party_role":"nope"})

    def test_optional_fields_none(self):
        r=store.save_wtp_raci_dependency({**BASE,"input":None,"output":None,"handoff":None,"dependency":None,"escalation":None,"critical_milestone":None,"evidence_status":None})
        for k in ("input","output","handoff","dependency","escalation","critical_milestone","evidence_status"):
            self.assertIsNone(r[k])

    def test_versioning_and_append_only(self):
        store.save_wtp_raci_dependency(BASE)
        r2=store.save_wtp_raci_dependency({**BASE,"task":"Nieuwe taak"})
        self.assertEqual(r2["version"],2)
        rows=store.wtp_raci_dependencies(customer_id="northstar",fund_ref="FUND-SYNTH-01")
        self.assertEqual(len(rows),2)
        import sqlite3
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE wtp_raci_dependencies SET task='x' WHERE id=?",(r2["id"],))
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM wtp_raci_dependencies WHERE id=?",(r2["id"],))

    def test_query_filters(self):
        store.save_wtp_raci_dependency(BASE)
        store.save_wtp_raci_dependency({**BASE,"party_role":"manager","party_name":"Manager (synthetisch)"})
        self.assertEqual(len(store.wtp_raci_dependencies(party_role="fiduciair")),1)
        self.assertEqual(len(store.wtp_raci_dependencies(party_role="manager")),1)

if __name__=="__main__":
    unittest.main()
