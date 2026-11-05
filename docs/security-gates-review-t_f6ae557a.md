# Security review — external gates and security boundaries (task t_f6ae557a)

Scope: worktree `wt/t_f6ae557a` (HEAD of reviewed chain). Reviewer: security profile. Method: read-only inspection of ADRs, discovery evidence, SEC-002 evidence, source (store.py), and test suite. No code modified; no approvals granted.

## Summary

All six named human gates remain **OPEN**. No evidence of owner appointment, enforcement-level definition, source classification policy, role matrix, FactSet confirmation, or identity provider confirmation was found in the repository. These are external blockers and are recorded as REQUEST CHANGES findings, not resolved.

## Findings (REQUEST CHANGES)

🔴 R-G1 — Policy owner appointment (CLIENT-PAI-DATA / WTP-TRANSITION-DATA / ICT-DORA-SCOPE)
Evidence: `docs/discovery/feature-1-discovery-evidence.md` states "No policy owner appointments"; ADR-0003 defers formal policy content to "Control-eigenaar + Compliance/Legal". No appointment record, owner name, or dated decision found anywhere in repo.
Required: Compliance/Legal + Client Service + ICT-risk to appoint validated owners per control. Until then, enforcement stays `manual`/`pending` and controls must not be presented as hard blocks.

🔴 R-G2 — Enforcement level and exception process per control
Evidence: discovery evidence marks "Enforcement levels (hard/soft/manual) — policy owner must define per control" as open. No per-control enforcement level or exception process document found.
Required: policy owner + Compliance to define per control with exception path and acceptance criteria.

🔴 R-G3 — Primary source classification policy
Evidence: no validated primary-source classification policy found; controls carry `validation_status=pending` / `source_ref` without validated classification.
Required: Compliance/Legal source review per control.

🔴 R-G4 — Validated role matrix and actor separation (SEC-002)
Evidence: `docs/feature-10-sec-002-evidence.md` and ADR-0005 list all SEC-002 acceptance criteria as Open (server-side authorization, initiator ≠ approver, limited admin roles, periodic access review). No role/capability matrix, group/role claim mapping, or access-review cadence documented.
Required: product owner + security owner approval of SEC-002 role/capability matrix.

🔴 R-G5 — FactSet tenant/service confirmation before any performance endpoint contract
Evidence: no FactSet tenant/service confirmation found; performance endpoint contracts must not be finalized until confirmed. (BENCH-002 reviewer already flags: do not build future performance engine/FactSet contract.)
Required: external confirmation recorded before contract finalization.

🔴 R-G6 — Identity provider/tenant confirmation (ADR-0005)
Evidence: ADR-0005 status "Accepted for preparation; identity provider selection remains open". Prototype uses fixed `Demo operator`; API mutations accept actor strings from browser requests. No tenant, provider, environment, or role mapping confirmed.
Required: platform/identity owner confirmation (provider discovery URL, client registration, callback/logout URLs, signing algorithms, key rotation, test tenant). Secrets via deployment secret manager, never Git.

## Security boundary checks performed (read-only)

- Secrets: scan of `app/` for hardcoded api_key/secret/password/token returned no matches. ✅ (no inlined secrets found in this pass)
- Tenant isolation / RLS: no multi-tenant enforcement or RLS present; single synthetic pilot. Not a production boundary; must be addressed before production. ⚠️
- Auditability: append-only triggers and bitemporal (valid time + transaction time) present per Feature 6/7 evidence. Actor values are demo inputs, not authoritative identity. ⚠️
- Approval boundaries: four-eyes simulated fee impact exists; no RBAC/ABAC enforced (deferred to SEC-002). ⚠️
- Append-only protections: present (update/delete protection verified by reviewer probes). ✅
- Auth/rate limits: explicitly unimplemented demo gates per ADR-0005. ⚠️

## Verdict

REQUEST CHANGES — all six external human gates remain open and must be resolved by their named owners before any production claim. No code changes made; no approval granted. Test suite baseline: 406 passed (this worktree).