# Feature 3 — POL-002 Broncontrole evidence

Task: t_b6b790c0 (builder)
Branch: wt/t_b6b790c0
Base: Feature 2 commit 1d77f00 (t_5f1ae7b6, review approved t_bb0d69a0)

## Scope
Source-review workflow built on POL-001 register:
- Append-only source reviews (`policy_source_reviews`, triggers no update/delete)
- Distinct-reviewer enforcement: `decide_policy` refuses validation when actor == source reviewer
- Derived validation status flips to `pending` when a newer source review arrives after a validated decision
- Source-review history retained (append-only, ordered by checked_at DESC)
- Unapproved interpretations surface as non-blocking signals via `policy_signals()`

## Test evidence
Command: `/opt/homebrew/bin/python3.14 -m unittest discover tests -v`
Result: 10 tests, 0 failures, exit 0

Tests cover:
- test_source_review_append_only (new record per review)
- test_distinct_reviewer_required_for_validation
- test_newer_source_review_flips_validation_to_pending
- test_source_review_history_remains_available_after_later_reviews
- test_validation_status_derived_not_stored
- test_unapproved_interpretations_surface_as_non_blocking_signals

## Human gates (explicit, not invented)
- Primary source classification policy — owner: Compliance/Legal (open)
- Actor separation in SEC-002 role matrix — owner: Security/Compliance (open)
- Policy owner appointment CLIENT-PAI-DATA / WTP-TRANSITION-DATA / ICT-DORA-SCOPE — owner: Compliance/Legal + Client Service + ICT-risk (open)
- Enforcement level per control + exception process — owner: policy owner + Compliance (open)

## Constraints honored
- Synthetic data only; no real customer data
- Append-only: no hard deletes; valid time + transaction time preserved
- No pre-existing user modifications overwritten (merged Feature 2 via fast-forward from main 4d05a66)
- SEC-001 identity implementation not touched (externally blocked per ADR-0005)
