# Feature 13 — OUT-001 Activiteitregister — Evidence

Datum: 2026-11-04 · Tak: `wt/t_57ced659` · Gebouwd op: main `3a952fc` (na reviewde merge van Features 8–12, parent-taak t_30b99bcc).

## Scope

Activiteitregister per relatie/klant: concrete werkzaamheden, grenzen, betrokken diensten, fonds-/mandaatrelatie, kritikaliteit/materialiteit, eigenaar en contractperiode, vastgelegd in een append-only, bitemporeel register (`activity_register`), met een ketenweergave (`activity_chain`) voor een fonds-/mandaatwijziging: het complete relevante beeld (activiteit, diensten, afhankelijkheden uit relaties en DORA-assessments), **missende contractvelden** en de huidige **review-/meldstatus**.

- `app/store.py`: tabel `activity_register` (PK `(id,version)`, `UNIQUE`-vrij, FK naar `customers`), append-only triggers (`activity_register_no_update` / `activity_register_no_delete`). Functies `activities(...)` (huidige + `valid_at`/`known_at` bitemporele read), `save_activity(...)` (versie-aanmaak, geen overwrite), `activity_chain(...)` (keten + `missing_contract_fields` + `review_status`).
- Kritikaliteit waarden `laag|gemiddeld|hoog`, materialiteit `immatérieel|materieel|zeer materieel` — domeinlabels, geen thresholds; er is **geen** DNB-30%-getal of vergelijkbare drempel hardcoded. Thresholds blijven bronverwijzingen/policyparameters (open gate).
- `review_status` in de keten is altijd `pending` zolang Compliance/Legal-validatie ontbreekt — een open human gate als signaal, geen blokkade en geen claim van compleetheid. (Zie validatienota: interpretatie Pensioenwet art. 34, Wft art. 3:18, Besluit uitvoering Pw/Wvb, Besluit prudentiële regels Wft.)
- `app/server.py`: append-only nieuwe routes `GET /api/activities`, `GET /api/v1/activities` (bitemporeel), `POST /api/activities`, `GET /api/customers/<id>/activity-chain/<activity-id>`. Bestaande routes onaangetast; geen gebruikerswijzigingen overschreven.
- `tests/test_activity_register.py`: 10 tests (positief, verplichte velden, versiegedrag, append-only delete-blokkade, contracteind-datumnegatief, keten-velden ontbreken/compleet, onbekende activiteit, valid-time filter, reviewstatus-signaal).

## Test-first (RED → GREEN)

1. RED: `python3.13 -m pytest tests/test_activity_register.py -q` → `10 failed` (alle fixtures `AttributeError`/missing functions) vóór implementatie.
2. MID: na eerste implementatie 8 failed → 2 implementatiefixes (`None`-check in required-velden; JSON-parsering voor `services`) en 1 placeholdercorrectie (20 kolommen/20 `?`).
3. GREEN: uiteindelijke full-suite run:

```
$ python3.13 -m pytest -q
.......................................................................  [100%]
71 passed in 2.16s
EXIT=0
```

61 bestaande + 10 nieuwe tests, exit 0. Bewaard in `/tmp/f13-final-suite.txt`.

## Live API smoke (synthetische gegevens)

- `POST /api/activities` → `201`, registreert `act-northstar-out-001-fid` v1 met diensten `[FIDUCIARY, RISK]`, fonds-/mandaatref, contractstart.
- `POST /api/activities` zonder `owner` → `400 {"error":"owner is verplicht"}` (negatief pad).
- `GET /api/customers/northstar/activity-chain/act-northstar-out-001-fid` → `200` met `services`, `fund_mandate_ref`, `missing_contract_fields:["contract_end"]`, `review_status:"pending"`, `validation_note:"te valideren door Compliance/Legal voor relevante klant/partij"`.
- `GET /api/v1/activities?valid_at=...&known_at=...` → bitemporele read, 200.
- Smoke-DB (`data/client_config.db`) verwijderd na de run (repo bevat geen klantdata; alleen synthetische seed).

## Gedrag en grenzen

- Append-only: inserts per versie; UPDATE/DELETE via triggers geweigerd (test `test_append_only_delete_blocked`, `test_versioned_no_overwrite`).
- Valid time (`effective_from`/`effective_to`) en transaction time (`created_at/created_by`) bewaard; bitemporele as-of-read getest.
- Audit: elke insert schrijft een `audit`-regel (entity_type `activity_register`) met actor, reden, versie en contractvelden.
- Geen nieuwe runtime-dependencies; SQLite-prototype behouden tot de PostgreSQL-slice.

## AI-audit vóór commit

- Geen secrets/keys in de diff; alleen synthetische identifiers (`SYNTHETIC-CONTRACT-001`, `demo.*` actoren).
- Invoervalidatie: verplichte velden, enum-checks voor kritikaliteit/materialiteit, ISO-datumchecks, contracteind ≥ contractstart, services tegen JSON-list met afwijzing van lege waarden.
- Geen SQL-interpolatie met gebruikersinput (alle queries geparametriseerd); chain-joins zijn read-only fouttolerant gegen de bestaande registers.
- Rate limiting / auth: out of scope — de demo-server is by design onbeveiligd tot SEC-001/SEC-002 gates (record, niet geïntroduceerd in deze feature).

## Open human gates (record, niet geïnventeerd)

Onveranderd t.o.v. de opdracht: policy owner-appointment CLIENT-PAI-DATA / WTP-TRANSITION-DATA / ICT-DORA-SCOPE; handhavingsniveau per control met uitzonderingsproces; primary source classification policy; gevalideerde rolmatrix en actoren-scheiding (SEC-002); FactSet tenant/servicebevestiging voor performance-endpoints; identity provider/tenant (ADR-0005). Daarnaast: kritikaliteits-/meldplicht-interpretatie (Pensioenwet art. 34, Wft art. 3:18) te valideren door Compliance/Legal.

## Committed bestanden

- `app/store.py` (schema + `activities`/`save_activity`/`activity_chain`)
- `app/server.py` (routes, append-only toevoeging)
- `tests/test_activity_register.py` (10 tests)
- `docs/feature-13-out-001-evidence.md` (dit bestand)

Geen gebruikersgewijzigde bestanden (`AGENTS.md`, `app/static/index.html`, `docs/*-UI-DESIGN-NOTES.md`, `docs/adr/*`) aangeraakt.
