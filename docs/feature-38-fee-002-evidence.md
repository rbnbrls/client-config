# Feature 38 — FEE-002 evidence (t_d45b089b)

Command: `python3.13 -m pytest -q` → 322 passed, exit 0 (26.24s).
`git diff --check` clean.

New tests: `tests/test_fee_calculation_rules.py` (17 tests) covering store validation/enums/versioning/append-only/export shape and domain round_money/fx_convert/apply_cap_floor/tiered_fee/minimum_fee/performance_fee/calculate_fee.

Implemented versionable shared fee calculation rules: `fee_calculation_rules` table (append-only triggers), `save_fee_calculation_rule`, `fee_calculation_rules`, `fee_calculation_rules_export` (generated_at/perimeter/coverage/rows), plus domain functions in `app/domain.py` (round_money, fx_convert, apply_cap_floor, tiered_fee, minimum_fee, performance_fee, calculate_fee). Synthetic data only. Open human gates recorded, not invented.