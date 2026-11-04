# Feature 41 — FEE-005 evidence

Command: `python3.13 -m pytest -q`
Result: 355 passed in 29.38s (exit 0)
git diff --check: clean

Implemented append-only `fee_simulation` table and helpers (save_fee_simulation, fee_simulation, fee_simulation_export) with versioning, required/enum validation, unknown customer handling, level filter, export with perimeter/coverage/generated_at. Tests verify shared domain function usage.
