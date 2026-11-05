# P0 Decision Register

Status: synthetic discovery baseline; production decisions remain gated.
Effective date: 2026-11-05
Review date: 2026-12-05
Source of truth: `PRODUCT_BACKLOG.md`, `docs/discovery/feature-1-discovery-evidence.md`, ADRs in `docs/adr/`.

## Decision rules

- Use synthetic identifiers and values only.
- Unresolved legal, customer, identity, and platform choices stay `OPEN` or `PROPOSED`.
- No unresolved choice may become a hard blocking policy.
- A hard block needs a confirmed owner, scope, authoritative source, exception path, and acceptance tests.

## Register

| ID | Decision | Status | Owner | Scope | Source | Effective | Review | Impact |
|---|---|---|---|---|---|---|---|---|
| D-001 | Pilot uses synthetic customer `PILOT-001`; real pilot selection stays open | PROPOSED | Customer/Mandate Owner | P0 discovery only | ADR-0012; feature-1 evidence | 2026-11-05 | 2026-12-05 | F01–F05 |
| D-002 | First chain is role-level: fund → fiduciary → asset manager → submanager → custodian | PROPOSED | Customer/Mandate Owner | Synthetic topology only | ADR-0012; CFG-001 evidence | 2026-11-05 | 2026-12-05 | F01, F06–F07 |
| D-003 | Fund, asset class, legal IDs, jurisdictions, and contract terms remain open | OPEN | Customer/Mandate Owner + Compliance | Selected pilot | ADR-0012; feature-1 evidence | — | 2026-12-05 | F01, F06, P8 |
| D-004 | Policy records are append-only and versioned | CONFIRMED prototype | Policy Owner | Prototype register | ADR-0003; `app/store.py` | 2026-11-05 | 2026-12-05 | F02–F05 |
| D-005 | Source review precedes policy decision; reviewer and decision-maker differ | CONFIRMED prototype | Compliance | Policy controls | Feature-1 evidence; policy tests | 2026-11-05 | 2026-12-05 | F03 |
| D-006 | Policy enforcement is per-control: hard, soft, or manual; default unresolved state is non-blocking | PROPOSED | Control Owner + Compliance/Legal | Each policy control | `PRODUCT_BACKLOG.md`; ADR-0003 | 2026-11-05 | 2026-12-05 | F02–F05 |
| D-007 | DORA, outsourcing, ESG, SFDR/PAI, and Wtp applicability require human review | OPEN | Compliance/Legal + ICT-risk | Customer/service specific | `PRODUCT_BACKLOG.md`; ADR-0002 | — | 2026-12-05 | F04–F05, P2–P5 |
| D-008 | Retention, legal holds, region, RTO/RPO, and auditor access need customer/platform approval | OPEN / proposed EU/EEA baseline | Platform Owner + Legal/Risk | Production platform | Regulatory policy baseline handoff | — | 2026-12-05 | P1–P8 |
| D-009 | Identity provider, tenant, claims, deployment, secrets, and role matrix remain blocking choices | OPEN | Identity/Platform Owner + Security | Production identity | ADR-0005 | — | 2026-12-05 | SEC-001/002 |
| D-010 | Emergency/break-glass authority remains blocked until explicit approval and post-event review are defined | OPEN | Security Owner + Product Owner | Production operations | ADR-0012 | — | 2026-12-05 | SEC-002, AUD-001 |
| D-011 | Partner export, performance engine, ADLS/orchestration, and BI/RLS choices require platform-owner confirmation | OPEN | Platform/Integration Owner | P7–P8 | `PRODUCT_BACKLOG.md`; implementation handoff | — | 2026-12-05 | INT-001, P8 |

## Acceptance gate

Feature 1 passes discovery only when every item has status, owner, scope, source, effective/review handling, and impacted work. Items marked OPEN do not authorize implementation or legal conclusions.
