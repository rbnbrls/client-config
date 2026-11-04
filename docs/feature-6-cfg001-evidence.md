# Feature 6 — CFG-001 Entiteiten en relaties: bewijs (evidence)

Taak: Kanban `t_d95fbd05` · Branch: `wt/t_d95fbd05` · Baseline: 45cc067 (goedgekeurde Feature 5) · Alle gegevens synthetisch.

## Wat is opgeleverd

1. **Dependency-keten hersteld (merge `5513cfe`)** — de POL-001/POL-002-featurelijn (`1d77f00` hard_block/policy_signals + `tests/test_policy_register.py`, `d3efdce` broncontrole-evidence) was op `main`/`4d05a66` geforkt en nooit samengevoegd met de POL-003→POL-004-keten. Feature 6 bouwt voort op álle goedgekeurde voorgaande features; de merge herstelt de enkelvoudige keten. Merge en testsluites hieronder zijn direct daarna gedraaid.
2. **Append-only triggers voor `client_entities` en `client_relationships`** — tot nu toe waren dit de enige registers zonder no-update/no-delete-triggers. Nieuw: `client_entities_no_update/_no_delete`, `client_relationships_no_update/_no_delete` (RAISE(ABORT)), conform "Records worden niet verwijderd; nieuwe versies en auditregels bewaren correcties" (PROJECT-PLAN.md, CFG-001).
3. **Bugfix: `NameError: name 'effective_to' is not defined`** — `save_client_entity` en `save_client_relationship` verwezen in de audit-ports naar een niet-gedefinieerde lokale variabele; élke registratie van een entiteit of relatie faalde daardoor. Nu wordt `effective_to` één keer afgeleid en consequent gebruikt in INSERT én audit-details.
4. **`tests/test_entities_relations.py` — 11 regressiontests** (test-first, RED vóór de fixes).

## TDD-bewijs

| Stap | Commando | Resultaat |
|---|---|---|
| Baseline vóór merge | `python3.14 -m unittest tests.test_client_variants tests.test_dora_assessments` | 10/10 OK (exit 0) |
| Na keten-merge | `python3.14 -m unittest tests.test_policy_register tests.test_client_variants tests.test_dora_assessments` | 20/20 OK (exit 0) |
| **RED** | `python3.14 -m unittest tests.test_entities_relations` | 11 tests, 11 errors — alle via `NameError: name 'effective_to' is not defined` (store.py:492); triggerbeweringen konden nog niet bereikt worden |
| **GREEN** | `python3.14 -m unittest tests.test_entities_relations` | 11/11 OK |
| **Volledige suite** | `python3.14 -m unittest tests.test_policy_register tests.test_client_variants tests.test_dora_assessments tests.test_entities_relations` | **31/31 OK, exit 0** |

## Dekking van de CFG-001-acceptatiecriteria (PROJECT-PLAN.md, P1)

| Criterium | Bewijs (test) |
|---|---|
| Versieerbare entiteiten per klant; correcties als nieuwe versie + audit | `test_entity_versioning_and_audit` (versies [1,2]; audit `created`+`versioned`) |
| Records niet verwijderbaar / append-only | `test_entity_append_only`, `test_relationship_append_only` (IntegrityError via nieuwe triggers) |
| Entiteitstypen: fonds, juridische entiteit, groep, fiduciair, manager, submanager, custodian, dienstverlener | `test_entity_type_allowlist`, `test_full_chain_synthetic_parties` |
| Getypeerde gerichte relaties (fiduciary_for, member_of_group, manages, subdelegates_to, custody_for, service_provider_for, parent_of, client_of) met dienstscope | `test_relationship_type_allowlist`, `test_full_chain_synthetic_parties` |
| Relaties vereisen bestaande entiteiten binnen dezelfde klant; niet naar zichzelf | `test_relationship_requires_entities_in_same_customer`, `test_relationship_self_reference_blocked` |
| Entiteit-ID's zijn per klant gescopeerd | `test_entity_id_scoped_to_customer` |
| Geldigheidsdata + geldigheidsfiltering in de graaf; hoofdklant blijft read-only root op het klantrecord | `test_valid_time_graph_filtering` (toekomstige `effective_from` absent/present; root `read_only`, type `customer`) |
| Relatiecorrecties als nieuwe versie + audit | `test_relationship_versioning_and_audit` |
| Bronreferentie en motivering verplicht | verplichte-veldcontrole in `save_client_entity`/`save_client_relationship`, gedekt via de helpercontracten in elke test |

## Status en open gates (expliciet, niet uitgevonden)

- **Geen productieautorisatie of volledige bitemporele opslag** — blijft open conform planregel CFG-001 ("De volledige P1-acceptatie voor productie blijft open"); volledige bitemporele reconstructie is Feature 7 (CFG-002).
- **Demo-actoren** (`demo.client-service`) zijn geen authenticatie; SEC-001 blijft extern geblokkeerd per ADR-0005 (provider/tenant/identity-owner/deployment — eigenaar: identity-owner + platform owner).
- **Enterprise-entity resolution** en historie vóór migratie: niet in deze slice (CFG-002/P1-gereedheidskloof).
- Known nit: `ResourceWarning: unclosed database` in de suite — pre-existent patroon (`with connect()` commit maar sluit niet) in de hele prototype-codebase, niet door deze feature geïntroduceerd; bewust niet in deze task aangepast.

## Scope-bewaking

- Geen gebruikerswijzigingen overschreven: `AGENTS.md`, `app/server.py`, `app/static/index.html`, `docs/SEC-001-UI-DESIGN-NOTES.md`, `docs/adr/0005-*` zijn niet gewijzigd (diff bevat uitsluitend `app/store.py`, `tests/test_entities_relations.py` en dit bewijsdocument; plus de merge-commit).
- Alleen synthetische gegevens (`Synthetische …`, `SYNTH-SRC-001`, `SYNTH-CONTRACT-001`); geen secrets in de diff (scan gedraaid).
