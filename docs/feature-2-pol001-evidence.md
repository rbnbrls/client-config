# Feature 2 — POL-001 Besluitenregister: test- en opleveringsbewijs

Task: `t_5f1ae7b6` · Worktree: `/Users/ruben/Code/client-config/.worktrees/t_5f1ae7b6` · Branch: `wt/t_5f1ae7b6` · Datum: 2026-11-04 · Alle gegevens synthetisch.

## Aanpak (test-first)

1. RED: `tests/test_policy_register.py` geschreven vóór implementatie (10 tests). Eerste run: 5 fouten (ontbrekende `store.hard_block` / `store.policy_signals`), 5 bestaande gedragingen reeds groen.
2. GREEN: minimale implementatie in `app/store.py` (+37 regels, uitsluitend nieuwe pure functies; geen gedragswijziging in bestaande paden, geen nieuwe runtime-dependencies, SQLite ongewijzigd).

## Geteste acceptatiecriteria (suite: `/opt/homebrew/bin/python3.14 -m unittest discover tests -v`, 10/10 OK, exit 0)

| # | Criterium | Test |
|---|---|---|
| 1 | Registerleespad toont owner, audience, source_ref, applicability, enforcement, effective_date, version, review_date, validation_status | `test_register_read_path_exposes_full_contract` |
| 2 | Harde blokkade geweigerd zonder validated-status én bewijs | `test_hard_block_refused_without_validated_status_and_evidence`, `test_hard_block_refused_for_soft_and_manual_enforcement` |
| 3 | Nieuwere bronreview na validatie zet afgeleide status terug op `pending` (ook hard_block geweigerd) | `test_newer_source_review_flips_validated_back_to_pending` |
| 4 | Policybesluit alleen van reviewer verschillend van bronreviewer | `test_policy_decision_requires_reviewer_distinct_from_source_reviewer`; plus regressie: bronreview door initiator geweigerd; besluit zonder geverifieerde bron geweigerd |
| 5 | Bronreviewhistorie blijft beschikbaar na latere reviews (append-only; hard-delete via SQL triggert SQLite ABORT) | `test_source_review_history_remains_available_after_later_reviews` |
| 6 | Niet-goedgekeurde interpretaties zijn niet-blokkerende signalen | `test_unapproved_interpretations_surface_as_non_blocking_signals`, `test_validated_controls_produce_no_signal` |

Append-only gedrag: SQLite-triggers op `policy_controls`, `policy_source_reviews` en `policy_decisions` blokkeren update/delete (regressie in test 5); valid time (`effective_date`) en transaction time (`created_at`, `checked_at`, `decided_at`) blijven ongewijzigd bewaard.

## Nieuwe domeinfuncties (gedeeld domein; production-path en twin delen dezelfde logica)

- `store.hard_block(control_code, version=None)` — weigert (ValueError) tenzij enforcement `hard`, afgeleide status `validated` én bewijs (gevalideerd besluit met geverifieerde bronreview en motivering). Soft/manual blokkeren nooit.
- `store.policy_signals()` — niet-blokkerende signalen (`severity='signal'`, `blocking=False`) voor niet-gevalideerde controls en controls met verstreken reviewdatum.

## Expliciete menselijke gates (uit Feature 1-discovery — NIET geïmplementeerd, uitdrukkelijk geblokkeerd)

| Open besluit | Eigenaar (verantwoordelijke rol) |
|---|---|
| Beleidsaanwijzing policy-eigenaar voor `CLIENT-PAI-DATA`, `WTP-TRANSITION-DATA`, `ICT-DORA-SCOPE` | Compliance/Legal + Client Service + ICT-risk |
| Handhavingsniveau (hard/soft/manual) per control mét uitzonderingsproces | Policy-eigenaar + Compliance/Legal |
| Primaire-bronclassificatiebeleid (welke bronnen gelden als geverifieerd primair) | Compliance/Legal |
| Actorscheiding bronreview ↔ besluit verankeren in SEC-002-rolmatrix | Security/Compliance + product owner |

Tot deze gates bevestigd zijn, blijven alle controls `pending`/`manual` en weigert `hard_block` — by design, getest.

## Out of scope (onveranderd)

SEC-001-identiteit (ADR-0005, extern geblokkeerd); PostgreSQL-migratie (latere P1-slice); beslissen over policy-eigenaren/handhavingsniveaus; promotie van ongeverifieerde compliance-claims naar harde controls; echte klantdata.

## Zelf-audit

- Geen secrets/keys in diff (gescand); alleen synthetische actoren en bronnen.
- Geen user-touched bestanden aangeraakt (AGENTS.md, app/server.py, app/static/index.html, docs/SEC-001-UI-DESIGN-NOTES.md, docs/adr/0005-*): `git status` toont uitsluitend `app/store.py` (+37) en nieuwe `tests/`.
- Geen hard deletes; alle registers append-only via triggers.

## Current-base verification (2026-11-06)

- Baseline: `3dc5944112ff2ebc98526f1e1f8e2bf0bd535fc1` (`main`).
- Focused command: `python3 -m unittest tests.test_policy_register -v` — 10/10 OK, exit 0.
- `git diff --check main...HEAD` — PASS; no working-tree changes before this evidence update.
- Scope check: POL-001 implementation already exists in `app/store.py`, `tests/test_policy_register.py` and this evidence file; no duplicate runtime code added.
- ResourceWarning messages from existing SQLite connection cleanup appeared during tests; they did not fail tests and remain outside POL-001 scope.
