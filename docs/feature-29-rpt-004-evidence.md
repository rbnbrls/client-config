# Feature 29 — RPT-004 evidence

Command: `python3.13 -m pytest -q`
Result: 233 passed, 0 failed (exit 0).

Changed files:
- app/store.py (comply_or_explain table + triggers; save_comply_or_explain, comply_or_explain)
- tests/test_comply_or_explain.py

Append-only verified via IntegrityError on UPDATE/DELETE.
Synthetic data only.
