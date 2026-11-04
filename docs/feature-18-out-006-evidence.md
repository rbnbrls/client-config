# Feature 18 — OUT-006 evidence

Command: `python3.13 -m pytest -q`
Result: 118 passed in 4.94s (exit 0).

Scope: ICT provider relation register brought to parity with dora_assessments:
bi-temporal filtering (valid_at/known_at), MAX(version) projection, required-field
and enum validation, customer existence check, ISO-date validation, audit entry.
Append-only triggers preserved. Dedicated tests/test_ict_provider_relations.py added.
