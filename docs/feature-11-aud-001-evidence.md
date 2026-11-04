# Feature 11 — AUD-001 Append-only audit — Evidence

**Task:** t_bd3105c6 · **Branch:** `wt/t_bd3105c6` · **Datum:** 2026-11-04
**Synthetische gegevens; geen echte klant- of financiële data.**

## Implementatie

`app/store.py`:

- `audit`-tabel uitgebreid met vastleggingskolommen: `old_value`, `new_value`,
  `evidence` (bronbewijs), `policy_version`, `schema_version`, `simulation`,
  `approval`, `activation`, `publication_status` — naast bestaande `actor`,
  `action`, `at`, `reason`, `details` (actor, actie, tijd, oude/nieuwe waarde,
  reden, bronbewijs, policy-/schema-versie, simulatie, goedkeuring, activatie
  en export/publicatiestatus).
- Append-only afgedwongen op DB-niveau met triggers `audit_no_update` en
  `audit_no_delete` (`RAISE(ABORT,'audit records are append-only')`) —
  passend bij de acceptatie "records zijn niet hard te verwijderen; audit is
  niet wijzigbaar via reguliere product-API". Er is geen product-API-pad dat
  auditrecords bijwerkt of verwijdert; de triggers blokkeren het ook direct op
  SQL-niveau.
- Migratie add-only voor bestaande SQLite-databases (`ALTER TABLE ADD COLUMN`
  per ontbrekende kolom); bestaande rijen blijven behouden, geen verwijdering.
- `audit()`-helper accepteert de nieuwe velden (dicts worden JSON-geserialiseerd);
  `audit_log()` parseert ze terug naar structuur.
- Levenscyclus-legging: `create_change` (oude/nieuwe waarde per patch-pad,
  reden als bronbewijs, schema-versie), `simulate` (simulatieresultaat),
  `approve` (goedkeuring met goedkeurder + tijdstip), `activate` (activatie),
  `export_config` (publicatiestatus + checksum als bronbewijs),
  `save_policy` / policy-besluit (policy-versie).

## Testresultaat (volledige suite)

Commando: `python3.13 -m pytest -q`

```
45 passed in 1.48s
```

Nieuw testbestand: `tests/test_audit_append_only.py` (5 tests) — dekt:

1. `test_audit_update_is_blocked` — UPDATE op audit wordt geblokkeerd (negatief pad).
2. `test_audit_delete_is_blocked` — DELETE op audit wordt geblokkeerd (negatief pad).
3. `test_audit_log_returns_rich_records` — gestructureerde auditlogregels.
4. `test_change_set_lifecycle_records_audit_fields` — created/simulated/approved/
   activated leggen oude/nieuwe waarde, reden, bronbewijs, schema-versie,
   simulatie, goedkeuring en activatie vast.
5. `test_export_records_publication_status_audit` — export/publicatiestatus in audit.

RED→GREEN: nieuwe tests faalden eerst (geen triggers, geen kolommen), daarna
groen na implementatie. Volledige suite (incl. bestaande 40 tests) blijft groen.

## Migratieprobe (bestaande database, oud schema)

Legacy-DB met oude `audit`-tabel (zonder extra kolommen/triggers), daarna
`store.init()`:

```
legacy update blocked: audit records are append-only
legacy row preserved: tester
```

Bestaande rijen blijven behouden; append-only triggers actief na migratie.

## Open human gates (vastgelegd, niet ingevuld)

- Policy-eigenaar-benoeming voor CLIENT-PAI-DATA / WTP-TRANSITION-DATA /
  ICT-DORA-SCOPE (Compliance/Legal + Client Service + ICT-risk).
- Afdwingingsniveau per control met uitzonderingsproces.
- Primaire-bronclassificatiebeleid.
- Gevalideerde rolmatrix en functiescheiding (SEC-002, ADR-0005).
- FactSet tenant/service-bevestiging vóór performance-endpointcontracten.
- Identity provider/tenant-bevestiging (ADR-0005, SEC-001).

Geen van deze gates is in deze feature geïmplementeerd of als afgerond geclaimd.
