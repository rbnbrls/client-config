"""CFG-001 Entiteiten en relaties — regression tests.

Covers the prototype acceptance criteria from docs/PROJECT-PLAN.md (P1 /
CFG-001): versioned entities and directed relationships per customer,
append-only storage with audit, relationship validation (existing entities
within the same customer, no self-reference, typed relation set) and
valid-time graph reads with a read-only customer root.

All data is synthetic. Each test runs against an isolated SQLite database so
the prototype demo database is never touched.
"""
import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("CLIENT_CONFIG_DB", tempfile.mkdtemp(prefix="cfg001-") + "/t.db")
from app import store  # noqa: E402


def isolated_db():
    handle, path = tempfile.mkstemp(suffix=".db", prefix="cfg001-")
    os.close(handle)
    os.unlink(path)
    store.DB_PATH = Path(path)
    store.init()


def make_customer(cid="cust-a", name="Synthetische Klant A"):
    """Register a synthetic customer with one baseline config version."""
    with store.connect() as db:
        db.execute("INSERT INTO customers VALUES(?,?,?,?,?,?)",
                   (cid, name, "pension_fund", "NL", "institutional", store.now()))
        db.execute("INSERT INTO config_versions(id,customer_id,version,valid_from,valid_to,"
                   "recorded_from,recorded_to,payload,change_id,schema_version) VALUES(?,?,?,?,?,?,?,?,?,?)",
                   (cid + "-cfg-v1", cid, 1, "2026-01-01", None, store.now(), None,
                    '{"name":"%s","synthetic":true}' % name, None, "1"))


def entity(cid="cust-a", **kw):
    base = dict(customer_id=cid, entity_type="fund", name="Synthetisch Fonds",
                jurisdiction="NL", classification="fund", effective_from="2026-01-01",
                source_ref="SYNTH-SRC-001", rationale="Synthetische registratie",
                actor="demo.client-service")
    base.update(kw)
    return store.save_client_entity(base)


def relationship(cid, frm, to, **kw):
    base = dict(customer_id=cid, from_entity_id=frm, to_entity_id=to,
                relationship_type="fiduciary_for", service_scope="Fiduciair beheer",
                effective_from="2026-01-01", source_ref="SYNTH-CONTRACT-001",
                rationale="Synthetische relatie", actor="demo.client-service")
    base.update(kw)
    return store.save_client_relationship(base)


class CFG001EntitiesTestCase(unittest.TestCase):
    def setUp(self):
        isolated_db()
        make_customer()

    def test_entity_versioning_and_audit(self):
        e = entity()
        corrected = entity(id=e["id"], name="Synthetisch Fonds II", rationale="Correctie naam")
        self.assertEqual(corrected["version"], 2)
        with store.connect() as db:
            versions = [r["version"] for r in db.execute(
                "SELECT version FROM client_entities WHERE id=? ORDER BY version", (e["id"],)).fetchall()]
        self.assertEqual(versions, [1, 2])
        audit = [a for a in store.audit_log() if a["entity_type"] == "client_entity" and a["entity_id"] == e["id"]]
        self.assertEqual(sorted(a["action"] for a in audit), ["created", "versioned"])

    def test_entity_append_only(self):
        e = entity()
        import sqlite3
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE client_entities SET name='x' WHERE id=?", (e["id"],))
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM client_entities WHERE id=?", (e["id"],))

    def test_entity_type_allowlist(self):
        with self.assertRaises(ValueError):
            entity(entity_type="spaceship")
        for t in ("legal_entity", "group", "fund", "fiduciary", "asset_manager",
                  "sub_manager", "custodian", "service_provider"):
            self.assertEqual(entity(entity_type=t)["entity_type"], t)

    def test_entity_id_scoped_to_customer(self):
        make_customer("cust-b", "Synthetische Klant B")
        e = entity("cust-a")
        with self.assertRaises(ValueError):
            entity(customer_id="cust-b", id=e["id"], entity_type="fiduciary")

    def test_valid_time_graph_filtering(self):
        e = entity(effective_from="2026-06-01")
        before = store.client_entities("cust-a", valid_at="2026-05-01")
        after = store.client_entities("cust-a", valid_at="2026-07-01")
        self.assertFalse(any(x["id"] == e["id"] for x in before))
        self.assertTrue(any(x["id"] == e["id"] for x in after))
        graph = store.client_graph("cust-a", valid_at="2026-07-01")
        root = graph["entities"][0]
        self.assertEqual(root["entity_type"], "customer")
        self.assertTrue(root["read_only"])
        self.assertEqual(root["id"], "cust-a")


class CFG001RelationshipsTestCase(unittest.TestCase):
    def setUp(self):
        isolated_db()
        make_customer()
        self.fund = entity(entity_type="fund", name="Synthetisch Fonds")
        self.fid = entity(entity_type="fiduciary", name="Synthetische Fiduciair")

    def test_relationship_versioning_and_audit(self):
        r = relationship("cust-a", self.fid["id"], self.fund["id"])
        corrected = relationship("cust-a", self.fid["id"], self.fund["id"],
                                 id=r["id"], service_scope="Fiduciair beheer (herzien)",
                                 rationale="Correctie dienstscope")
        self.assertEqual(corrected["version"], 2)
        with store.connect() as db:
            versions = [row["version"] for row in db.execute(
                "SELECT version FROM client_relationships WHERE id=? ORDER BY version", (r["id"],)).fetchall()]
        self.assertEqual(versions, [1, 2])
        audit = [a for a in store.audit_log() if a["entity_type"] == "client_relationship" and a["entity_id"] == r["id"]]
        self.assertEqual(sorted(a["action"] for a in audit), ["created", "versioned"])

    def test_relationship_append_only(self):
        r = relationship("cust-a", self.fid["id"], self.fund["id"])
        import sqlite3
        with store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("UPDATE client_relationships SET service_scope='x' WHERE id=?", (r["id"],))
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM client_relationships WHERE id=?", (r["id"],))

    def test_relationship_type_allowlist(self):
        with self.assertRaises(ValueError):
            relationship("cust-a", self.fid["id"], self.fund["id"], relationship_type="owns")
        for t in ("member_of_group", "parent_of", "fiduciary_for", "manages",
                  "subdelegates_to", "custody_for", "service_provider_for", "client_of"):
            # Each type needs a fresh target to avoid duplicate-name noise; reuse is fine.
            r = relationship("cust-a", self.fid["id"], self.fund["id"], relationship_type=t)
            self.assertEqual(r["relationship_type"], t)

    def test_relationship_self_reference_blocked(self):
        with self.assertRaises(ValueError):
            relationship("cust-a", self.fund["id"], self.fund["id"])

    def test_relationship_requires_entities_in_same_customer(self):
        with self.assertRaises(ValueError):
            relationship("cust-a", "onbekende-entiteit", self.fund["id"])
        make_customer("cust-b", "Synthetische Klant B")
        foreign = entity("cust-b", entity_type="custodian", name="Synthetische Custodian B")
        with self.assertRaises(ValueError):
            relationship("cust-a", foreign["id"], self.fund["id"])

    def test_full_chain_synthetic_parties(self):
        group = entity(entity_type="group", name="Synthetische Groep")
        fiduciary = self.fid
        manager = entity(entity_type="asset_manager", name="Synthetische Beheerder")
        sub = entity(entity_type="sub_manager", name="Synthetische Subbeheerder")
        custodian = entity(entity_type="custodian", name="Synthetische Bewaarder")
        provider = entity(entity_type="service_provider", name="Synthetische Dienstverlener")
        relationship("cust-a", fiduciary["id"], self.fund["id"], relationship_type="fiduciary_for")
        relationship("cust-a", self.fund["id"], group["id"], relationship_type="member_of_group")
        relationship("cust-a", manager["id"], self.fund["id"], relationship_type="manages")
        relationship("cust-a", manager["id"], sub["id"], relationship_type="subdelegates_to")
        relationship("cust-a", custodian["id"], self.fund["id"], relationship_type="custody_for")
        relationship("cust-a", provider["id"], self.fund["id"], relationship_type="service_provider_for")
        rels = store.client_relationships("cust-a")
        types = {r["relationship_type"] for r in rels}
        self.assertLessEqual({"fiduciary_for", "member_of_group", "manages",
                              "subdelegates_to", "custody_for", "service_provider_for"}, types)
        entities = store.client_entities("cust-a")
        self.assertLessEqual({"fund", "group", "fiduciary", "asset_manager",
                              "sub_manager", "custodian", "service_provider"},
                             {e["entity_type"] for e in entities})
        by_type = {r["relationship_type"]: r for r in rels}
        self.assertEqual(by_type["fiduciary_for"]["from_name"], "Synthetische Fiduciair")
        self.assertEqual(by_type["fiduciary_for"]["to_name"], "Synthetisch Fonds")


if __name__ == "__main__":
    unittest.main()
