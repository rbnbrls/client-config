# Feature 45 — EXP-001 Partnerprofielen evidence

Command: `python3.13 -m pytest -q`
Result: 389 passed in 31.68s (exit 0)

Tests: tests/test_partner_profiles.py (11 tests) covering save_basic, required-field, unknown-customer, mapping/validation type checks, classification/privacy non-empty, append-only triggers, versioning, reproducibility, list filters, export equivalence, contract_test field.

Implementation: append-only `partner_profiles_versions` table with versioning, mapping/validation/classification/privacy_filter/contract_test, required-field and unknown-customer validation, list filters, export. Functions: save_partner_profile, partner_profiles, partner_profile_export (with aliases).
`git diff --check`: clean.
Synthetic data only; no hard deletes; valid+transaction time preserved via created_at/version.
Open human gates recorded (not invented): policy owners, enforcement levels, source classification, SEC-002 role matrix, FactSet tenant, identity provider/ADR-0005.
