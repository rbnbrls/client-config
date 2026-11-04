# Feature 37 — FEE-001 Fee-componenten evidence

Command: `python3.13 -m pytest -q`
Result: 291 passed in 21.82s (exit 0)

Implementation: append-only `fee_components` table in app/store.py with triggers; save_fee_component, fee_components, fee_components_export. Enums FEE_COMPONENT_TYPES, FEE_FREQUENCIES, FEE_CURRENCIES. Append-only verified via triggers.

Synthetic data only. No pre-existing user-modified files overwritten.
