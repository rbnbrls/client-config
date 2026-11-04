# Feature 18 — OUT-006 DORA/ICT-loskoppeling evidence

Command: python3.13 -m pytest -q
Result: 110 passed in 4.74s, exit 0

Implementation: append-only ict_provider_relations table with no_update/no_delete triggers, valid/transaction time, save_ict_provider_relations and ict_provider_relations store functions.
