# Phase P3 merge evidence — Features 20–25 into main

Date: 2026-11-04 (CET). Executed by @release (gate task t_cad7e632).

## Scope

Merged reviewed feature commits for Features 20–25 (ESG-001..ESG-006) into `main`
in numeric order, all `--no-ff`, zero conflicts. Full suite green.

## Merges (numeric order)

| Feature | ESG | Reviewed HEAD | Merge commit |
|---|---|---|---|
| 20 | ESG-001 Beleidsprofiel | 5d127aa | 511a82c |
| 21 | ESG-002 Managerselectie | 6de6b1d | 1ba5bbe |
| 22 | ESG-003 Contractuele flow-down | 548d6c7 | f9e2eaa |
| 23 | ESG-004 Due-diligencedossier | aa66e89 | 27717db |
| 24 | ESG-005 Engagement en incidenten | 5619f62 | 8f83998 |
| 25 | ESG-006 Periodieke beoordeling | a75078d | c75ff30 |

Merge-commit SHAs backfilled from `main` history by the Phase P4 gate
(task t_c0ce14c7, @release, 2026-11-04); each verified against the recorded
reviewer-approved HEAD above.

## Full suite

Command: `python3.13 -m pytest -q`
Result: `202 passed in 10.33s` (exit 0).

## Notes

No conflicts. User-touched files preserved. No production deploy, tagging, or Coolify.
