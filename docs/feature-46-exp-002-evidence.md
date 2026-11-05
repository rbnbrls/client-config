# Feature 46 — EXP-002 Publicatiestatus evidence

Command: python3.13 -m pytest -q
Result: 396 passed in 44.55s (exit 0)

git diff --check: clean
New tests: tests/test_publication_status.py (7 passed)
New table: publication_status_versions (append-only, no UPDATE/DELETE triggers)
Synthetic data only; valid+transaction time preserved.