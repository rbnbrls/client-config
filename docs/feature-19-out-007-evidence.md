# Feature 19 (OUT-007) evidence

## Test run (round 2 — after adding tests/test_governance_policies.py)

Command: `python3.13 -m pytest -q`

```
........................................................................ [ 53%]
..............................................................           [100%]
134 passed in 6.33s
```

Exit 0. Suite grew from 118 (Feature 18 baseline) to 134: 16 new tests in
`tests/test_governance_policies.py` cover — required-field validation (each
required field blanked → ValueError), invalid `applicability` enum, invalid
`reviewer_role`, ISO-date validation on `effective_from`/`review_date`/
`evaluation_date`, `effective_to <= effective_from` rejection (both `<` and `==`),
`effective_to > effective_from` accepted, unknown `customer_id`, platform-level
record without customer, append-only UPDATE/DELETE trigger rejection, versioning
via MAX(version) projection, valid-time filtering, known-at filtering, customer
filtering, and audit entry (`created` + `versioned` actions).

## Implementation

Append-only `governance_policies` register capturing fondsbeleid,
monitoringfrequentie, rapportage, escalatie, onafhankelijke evaluatie,
capaciteit en evaluatiedatum, with bi-temporal filtering (`valid_at`/`known_at`),
MAX(version) projection, required-field and enum validation, customer check,
ISO-date validation, and audit entry. Thresholds/review dates are source-referenced
policy parameters (`source_ref`), not hardcoded values.

## Changed files (round 2)

- `tests/test_governance_policies.py` (new, 16 tests)
- `docs/feature-19-out-007-evidence.md` (this file, refreshed)

## Open human gates (recorded, not invented)

- Policy owner appointment for CLIENT-PAI-DATA / WTP-TRANSITION-DATA / ICT-DORA-SCOPE (Compliance/Legal + Client Service + ICT-risk).
- Enforcement level per control with exception process.
- Primary source classification policy.
- Validated role matrix and actor separation (SEC-002).
- FactSet tenant/service confirmation before any performance endpoint contract.
- Identity provider/tenant confirmation (ADR-0005).
- OUT-007 interpretation (Pensioenwet art. 34, Wft art. 3:18, Besluit uitvoering
  Pw/Wvb, Besluit prudentiële regels Wft, kritikaliteit en meldplicht): te
  valideren door Compliance/Legal voor relevante klant/partij.
