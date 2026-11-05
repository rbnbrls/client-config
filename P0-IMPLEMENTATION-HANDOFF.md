# P0 Implementation Handoff

Date: 2026-11-05
Feature: F01 domain/legal discovery
Decision register: `DECISION-REGISTER.md`

## Ready for downstream prototype work

- Synthetic pilot fixture and role-level manager-chain topology.
- Append-only policy/source-review/decision shapes.
- Non-blocking default for unresolved policy applicability.
- Data dictionary and bitemporal conventions in `docs/discovery/feature-1-discovery-evidence.md` and ADR-0002..0005.

## Blocked until human decision

| Gate | Owner | Required before |
|---|---|---|
| Real pilot fund, asset class, parties, legal identifiers, contract scope | Customer/Mandate Owner + Compliance | Production pilot and CFG-001 |
| Policy owner, scope, source classification, enforcement, exception and review cadence | Control Owner + Compliance/Legal | Any hard policy block |
| DORA/outsourcing/ESG/SFDR/PAI/Wtp applicability | Compliance/Legal + ICT-risk | Legal classification or regulatory conclusion |
| Retention, legal hold, region, RTO/RPO, auditor access | Platform Owner + Legal/Risk | Production storage and recovery |
| Identity provider, tenant, claims, deployment, secrets, role matrix | Identity/Platform Owner + Security | SEC-001/SEC-002 |
| Emergency authority and break-glass review | Security Owner + Product Owner | Emergency production path |

## Implementation boundary

Prototype work may use synthetic data and human-review states. Do not use caller-provided actor values as production identity, infer universal legal obligations, or turn `OPEN`/`PROPOSED` decisions into hard blocks. No production rollout authorized.

## Evidence

- `docs/discovery/feature-1-discovery-evidence.md`
- `DECISION-REGISTER.md`
- `docs/adr/0002-dora-assessment-valid-time.md`
- `docs/adr/0003-policy-valid-time.md`
- `docs/adr/0004-versioned-configuration-schemas.md`
- `docs/adr/0005-identity-and-sso-foundation.md`
- `PRODUCT_BACKLOG.md`
