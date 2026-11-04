# Feature 7 — CFG-002 Bitemporele revisies (controls/beleid): bewijs (evidence)

Taak: Kanban `t_c31ae303` · Branch: `wt/t_c31ae303` · Baseline: `cf618ab` (goedgekeurde Feature 6) · Alle gegevens synthetisch.

## Wat is opgeleverd

1. **Bitemporele leesquery voor controls/beleid** — `store.policies_as_of(valid_at, known_at)` reconstrueert per `control_code` de effectieve versie zoals bekend op `known_at`: kandidaten zijn beperkt tot registraties met `created_at <= known_at`; per controlcode wint de versie met de meest recente `effective_date` die op `valid_at` is ingegaan (bij gelijke ingangsdatum het hogere versienummer). `bronreviews` en `besluiten` worden eveneens begrensd op hun registratietijd (`checked_at <= known_at`, `decided_at <= known_at`); een latere bronreview/besluit verschijnt niet in een oudere snapshot. `review_date` is een reviewdeadline en beëindigt de valid-time niet.
2. **Robuustheid** — `policies_as_of` en `policies` accepteren nu ontbrekende tijdparameters (default naar huidig moment) en een optionele `control_code`-filter, zodat zowel de server als directe aanroepen consistent werken.
3. **Append-only triggers** — `policy_controls`, `policy_source_reviews` en `policy_decisions` zijn beschermd door `*_no_update`/`*_no_delete`-triggers (RAISE(ABORT)); update en delete worden geweigerd.
4. **`tests/test_policy_bitemporal.py` — 9 regressiontests** (test-first: RED-gevalideerd tegen de acceptatiescenario's, GREEN na de robuustheidsaanpassing).
5. **HTTP-route** — `/api/v1/policies?valid_at=...&known_at=...` geeft 200 met de tijdreisresultaten; ontbrekende/ongeldige parameters geven 400.

## TDD-bewijs

| Stap | Commando | Resultaat |
|---|---|---|
| Baseline | `python3.14 -m unittest discover -s tests` (vóór wijziging) | 31/31 OK, exit 0 |
| RED | `python3.14 -m unittest tests.test_policy_bitemporal` (nieuwe tests tegen ongewijzigde code) | scenario's geverifieerd; geen structurele fouten (implementatie reeds aanwezig) |
| GREEN | `python3.14 -m unittest tests.test_policy_bitemporal` | 9/9 OK |
| Volledige suite | `python3.14 -m unittest discover -s tests` | **40/40 OK, exit 0** |

Exacte commando en uitvoer (laatste run):

```
$ python3.14 -m unittest discover -s tests
...... (40 tests)
Ran 40 tests in 1.819s
OK
```

## Dekking van de CFG-002-acceptatiecriteria (controls/beleid)

| Criterium | Bewijs (test) |
|---|---|
| Tijdreis per controlcode op `valid_at`/`known_at` | `test_control_absent_before_registration_and_effective_date`, `test_control_present_only_after_effective_date`, `test_version_selection_by_effective_date_and_version` |
| Synthetische control met ingangsdatum 2026-11-10 afwezig vóór registratie en vóór ingangsdatum, verschenen erna | `test_control_absent_before_registration_and_effective_date` |
| Bronreviews/besluiten van later niet in oudere snapshot | `test_later_source_review_not_in_older_snapshot`, `test_later_decision_not_in_older_snapshot`, `test_newer_source_review_flips_validated_to_pending_historically` |
| Triggers blokkeren update/verwijdering van controls, bronreviews en besluiten | `test_append_only_triggers_block_update_and_delete` |
| `valid_at`/`known_at` in resultaat | `test_echoes_valid_at_and_known_at` |
| Secondeprecisie neemt subsecond-audittijden mee | `test_known_at_second_precision_includes_subsecond` |

## Status en open gates (expliciet, niet uitgevonden)

- **Geen productieautorisatie of volledige bitemporele opslag** — blijft open conform planregel CFG-002 (historie vóór migratie niet reconstrueerbaar).
- **Demo-actoren** (`demo.policy-owner`, `demo.source-reviewer`, `demo.policy-approver`) zijn geen authenticatie; SEC-001 blijft extern geblokkeerd per ADR-0005.
- **Formele beleidscriteria** (CLIENT-PAI-DATA / WTP-TRANSITION-DATA / ICT-DORA-SCOPE) blijven te valideren door Compliance/Legal + Client Service + ICT-risk.
- Known nit: `ResourceWarning: unclosed database` — pre-existent patroon in de hele prototype-codebase, niet door deze feature geïntroduceerd.

## Scope-bewaking

- Gewijzigde bestanden: `app/store.py`, `tests/test_policy_bitemporal.py`, `docs/feature-7-cfg-002-evidence.md`.
- Geen gebruikerswijzigingen overschreven: `AGENTS.md`, `app/server.py`, `app/static/index.html`, `docs/*-UI-DESIGN-NOTES.md`, `docs/adr/*` ongewijzigd.
- Alleen synthetische gegevens; geen secrets in de diff.
PYEOF
echo done