# Feature 33 — WTP-002 RACI en afhankelijkheden

## Implementation
- `app/store.py`: append-only versioned register `wtp_raci_dependencies` (table + index + no-update/no-delete triggers) plus `save_wtp_raci_dependency` and `wtp_raci_dependencies` query. Party roles enum: fonds, PUO, fiduciair, manager, custodian, technologiepartij.
- Fields: customer_id, fund_ref, party_role, party_name, task, input, output, handoff, dependency, escalation, critical_milestone, evidence_status, source_ref, rationale, created_by, created_at; versioned by (id, version).

## Tests
- `tests/test_wtp_raci_dependencies.py`: 8 passed.
- Full suite: `python3.13 -m pytest -q` → 269 passed, exit 0 (18.98s).

## Human gates (recorded, not invented)
Policy controls CLIENT-PAI-DATA / WTP-TRANSITION-DATA / ICT-DORA-SCOPE pending; PW/BuPW wettelijke interpretatie and fondsspecifieke datalijst/rekenverantwoordelijkheid to be validated by klant, pensioenexpert, Compliance/Legal; SEC-002 validated role matrix and actor separation; ADR-0005 identity/tenant; FactSet tenant/service confirmation.
