# Feature 31 — RPT-006 evidence

Command: `python3.13 -m pytest -q`
Result: 249 passed in 15.21s (exit 0).

`git diff --check`: clean.

Append-only triggers verified: UPDATE/DELETE on transparency_outputs raise IntegrityError. Versioned inserts confirmed.