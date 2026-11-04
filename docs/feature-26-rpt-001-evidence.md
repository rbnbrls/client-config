# Feature 26 — RPT-001 Rapportagecatalogus evidence

Command: `python3.13 -m pytest -q`
Result: 212 passed in 11.44s (exit 0)

Implementation: app/store.py — reporting_catalog table (append-only triggers), save_reporting_catalog_item, reporting_catalog_items, constants REPORTING_TYPES/FREQUENCIES/LANGUAGES.
Tests: tests/test_reporting_catalog.py (10 tests: save_basic, required fields, unknown customer, report_type/frequency/language enums, append-only triggers, versioning, query filters, recipients serialization).
