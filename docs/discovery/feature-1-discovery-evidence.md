# Feature 1 — Domein- en Legal Discovery Evidence

**Task:** `t_3151cf55` | **Assignee:** Architect | **Status:** Discovery Complete — Awaiting Independent Review
**Timestamp:** 2026-11-04T09:15:00+01:00
**Branch:** `client-config-project/t_3151cf55-feature-1-domein--en-legal-discovery`
**Workspace:** `/Users/ruben/Code/client-config/.worktrees/t_3151cf55`

---

## 1. Pilot Profile (Confirmed Synthetic; Human Selection Required)

| Element | Current Prototype Value | Decision Status | Owner/Action Needed |
|---------|------------------------|-----------------|---------------------|
| Pilot fonds / klant | `Northstar Pensioenfonds (synthetisch)` — ID `northstar` | **OPEN** — Human must select real pilot fonds | Klant-/Mandaat-eigenaar + Compliance |
| Asset class scope | Multi-asset (synthetisch benchmark "Synthetic Global 60/40") | **OPEN** | Klant-/Mandaat-eigenaar |
| Fiduciair manager | `Northstar Fiduciair (synthetisch)` — entity type `fiduciary` | **OPEN** | Klant-/Mandaat-eigenaar |
| Asset manager keten | `Northstar Asset Manager (synthetisch)` → `Submanager A (synthetisch)` | **OPEN** | Klant-/Mandaat-eigenaar |
| Custodian | `Northstar Custodian (synthetisch)` | **OPEN** | Klant-/Mandaat-eigenaar |
| Partner export schema | `generic-asp-v1.json` (synthetisch) | **OPEN** | Platform/Integration eigenaar |

> **Evidence:** `app/store.py:17-24` seeds three synthetic customers (`northstar`, `harbor`, `meridian`) with synthetic configurations. No real customer data exists in the repository. The task explicitly requires human confirmation of pilot profile before any implementation.

---

## 2. First Service/Manager Chain (Current Prototype Topology)

```
Customer (northstar)
  ├─ Legal Entity: Northstar Pensioenfonds (role: client)
  ├─ Service: FIDUCIARY (active) → Fiduciary Manager entity
  ├─ Service: RISK (active)
  ├─ Mandate: Strategisch mandaat
  │    ├─ Benchmark: Synthetic Global 60/40
  │    ├─ Currency: EUR
  │    └─ Delegation: Advisory
  ├─ Fees: AUM 18 bps, minimum €45k, quarterly
  ├─ SLA: rapportage_tijdigheid 98% quarterly
  ├─ Reporting: quarterly, 10 business days, NL
  ├─ Governance: Beleggingscommissie, escalation Client lead → Risk
  └─ Evidence: SYNTHETIC-CONTRACT-001 (example only)
```

**Relationships (CFG-001 prototype):**
- Fiduciary → Fund: `fiduciary_for`
- Fund → Group: `member_of_group` (not yet seeded for northstar)

**Decision Status:** All entities and relationships are **synthetic placeholders**. Human must confirm:
- Real legal entities, LEI identifiers, jurisdictions
- Actual service scope per relationship
- Contractual delegation model (Advisory/Discretionary/Execution)
- Fee schedules, tiers, performance fees, currency terms

> **Evidence:** `app/store.py:18-24` (seed), `app/store.py:88-101` (entity/relationship tables), `schemas/configuration-v1.json` (schema structure)

---

## 3. Data Dictionary (Prototype Coverage)

| Domain | Table / Schema | Key Fields | Versioning | Bitemporal | Status |
|--------|----------------|------------|------------|------------|--------|
| **Customers** | `customers` | id, name, kind, jurisdiction, classification | — | — | Prototype |
| **Config Versions** | `config_versions` | customer_id, version, valid_from, valid_to, recorded_from, recorded_to, payload, schema_version | Append-only | ✅ valid_at + known_at | Prototype |
| **Config Knowledge Snapshots** | `config_knowledge_snapshots` | customer_id, revision, recorded_at, actor, reason, timeline | Append-only | ✅ | Prototype |
| **Client Requirements** | `client_requirements` | id, version, customer_id, category, title, requirement, source_ref, config_path, expected_value, frequency, effective_date, review_date | Append-only per (id, version) | ✅ via graph_knowledge_snapshots | Prototype |
| **DORA Assessments** | `dora_assessments` | id, version, assessment_type, customer_id, counterparty, service_name, scope, applicability, criticality, contract_ref, source_ref, reviewer, reviewer_role, rationale, review_date, created_at, effective_from, effective_to | Append-only per (id, version) | ✅ explicit effective_from/effective_to + known_at | Prototype |
| **Client Entities** | `client_entities` | id, version, customer_id, entity_type, name, legal_identifier, jurisdiction, classification, effective_from, effective_to, source_ref, rationale | Append-only per (id, version) | ✅ via graph_knowledge_snapshots | Prototype |
| **Client Relationships** | `client_relationships` | id, version, customer_id, from_entity_id, to_entity_id, relationship_type, service_scope, effective_from, effective_to, source_ref, rationale | Append-only per (id, version) | ✅ via graph_knowledge_snapshots | Prototype |
| **Policy Controls** | `policy_controls` | id, control_code, version, title, owner, audience, source_ref, applicability, enforcement, effective_date, review_date, validation_status, validation_evidence | Append-only per (control_code, version) | ✅ effective_date + created_at + known_at | Prototype |
| **Policy Source Reviews** | `policy_source_reviews` | id, control_code, policy_version, source_kind, source_title, source_locator, outcome, reviewer, reviewer_role, rationale, checked_at | Append-only | transaction-time only | Prototype |
| **Policy Decisions** | `policy_decisions` | id, control_code, policy_version, source_review_id, decision, reviewer, reviewer_role, rationale, decided_at | Append-only | transaction-time only | Prototype |
| **Config Schemas** | `config_schema_versions` | version, schema_id, title, owner, effective_from, recorded_at, schema_json | Append-only (immutable) | recorded_at as transaction-time | Prototype |
| **Change Sets** | `change_sets` | id, title, customer_id, base_version, patch, effective_date, rationale, status, created_by, created_at, simulation, approved_by, approved_at, activated_at, schema_version | Append-only | effective_date as valid-time | Prototype |
| **Audit Log** | `audit` | entity_type, entity_id, action, actor, reason, at, details | Append-only | transaction-time (at) | Prototype |
| **Exports** | `exports` | id, customer_id, config_version, profile_id, schema_version, checksum, payload, status, created_by, created_at | Append-only | — | Prototype |
| **Partner Profiles** | `partner_profiles` | id, name, schema_version, mapping | — | — | Prototype |

**Open Data Dictionary Decisions (Human Required):**
- [ ] **Legal identifier standards** (LEI, KvK, RSIN, custom) per entity type
- [ ] **Jurisdiction taxonomy** (ISO 3166 + sector-specific)
- [ ] **Classification taxonomy** for entities (regulated/unregulated, AIFMD, UCITS, etc.)
- [ ] **Relationship type extensibility** (current: 8 types; need governance for additions)
- [ ] **Category taxonomy for client_requirements** (current: 8; validate with Compliance/Legal)
- [ ] **DORA assessment_type taxonomy** (current: 3; validate with ICT-risk + Compliance/Legal)
- [ ] **Criticality taxonomy** (current: 3; align with DNB guidance)
- [ ] **Enforcement levels** (hard/soft/manual) — policy owner must define per control

> **Evidence:** `app/store.py` (full schema), `schemas/configuration-v1.json`, `schemas/client-requirements-api-v1.json`, `schemas/dora-assessments-api-v1.json`, `schemas/policies-api-v1.json`, `schemas/config-schemas-api-v1.json`, ADR-0002, ADR-0003, ADR-0004

---

## 4. Policy Owners (Current Prototype Assignments — All Require Human Confirmation)

| Control Code | Title | Prototype Owner | Prototype Audience | Status | Human Owner Needed |
|--------------|-------|-----------------|-------------------|--------|-------------------|
| `CLIENT-PAI-DATA` | PAI-data-aanlevering per mandaat | `Compliance (te bevestigen)` | Klant / mandaat / manager | `pending` | **Compliance eigenaar + Legal** |
| `WTP-TRANSITION-DATA` | Wtp-transitiedata en mijlpalen | `Client Service (te bevestigen)` | Pensioenfonds / vermogensbeheerketen | `pending` | **Client Service lead + Compliance** |
| `ICT-DORA-SCOPE` | Classificatie ICT- en vermogensbeheerdienst | `Compliance (te bevestigen)` | Dienstverlener / contract | `pending` | **Compliance + ICT-risk + Legal** |

**Policy Governance Rules (Enforced in Prototype):**
- Source review required before validation decision (`app/store.py:600-601`)
- Reviewer ≠ Initiator (`app/store.py:605`)
- Decision reviewer ≠ Source reviewer (`app/store.py:623-625`)
- Enforcement levels: `hard` (blocking), `soft` (signal), `manual` (human review) — **must be defined per control by owner**

**Open Policy Owner Decisions:**
- [ ] Formal owner assignment per control (name, role, contact, escalation path)
- [ ] Scope definition per control (which customers, funds, mandates, services)
- [ ] Source classification policy (what counts as primary_regulatory vs customer_contract vs customer_policy)
- [ ] Exception process per control (who approves, criteria, evidence, expiry)
- [ ] Review cadence and ownership (review_date is deadline only; process undefined)

> **Evidence:** `app/store.py:131-138` (seed_policies), `app/store.py:512-630` (policy workflow), ADR-0003, PROJECT-PLAN.md lines 48-59

---

## 5. Unresolved ADR Decisions (Open Gates)

| ADR | Title | Status | Open Decisions | Owner |
|-----|-------|--------|----------------|-------|
| **ADR-0002** | DORA Assessment Valid Time | Prototype convention | Formal DORA scope/kritikaliteit criteria; legal applicability per client/service | Compliance/Legal + ICT-risk |
| **ADR-0003** | Policy Valid Time (Controls) | Prototype convention | Formal policy content, enforcement thresholds, exception process | Control-eigenaar + Compliance/Legal |
| **ADR-0004** | Versioned Configuration Schemas | Prototype decision | Schema owners per parameter; client/mandate-specific norms; JSON Schema subset extensions | Domeineigenaars per parameter |
| **ADR-0005** | Identity & SSO Foundation | **Accepted for preparation only** | **Provider (Entra ID vs enterprise OIDC), Tenant, App registration, Deployment, Secrets management, Claim mapping, Role matrix (SEC-002)** | **Platform/Identity Owner (BLOCKING SEC-001)** |

**ADR-0005 Preparation Deliverables (Must Be Completed Before SEC-001 Implementation):**
1. Identity provider and tenant/environment owner confirmed ✅ **OPEN**
2. Provider discovery URL, client registration, callback/logout URLs, signing algorithms, key rotation, test tenant documented ✅ **OPEN**
3. Stable subject claim (`iss` + `sub`) mapped to internal actor identifier ✅ **OPEN**
4. SEC-002 role/capability matrix approved by product owner and security owner ✅ **OPEN**
5. Migration inventory: every API mutation accepting actor string ✅ **PARTIAL** (see `app/server.py` mutations)
6. Session store, cookie domain, TLS termination, reverse-proxy trust, logout, recovery, monitoring, operational ownership documented ✅ **OPEN**
7. Synthetic test identities and non-production identity environment available ✅ **OPEN**

> **Evidence:** `docs/adr/0002-dora-assessment-valid-time.md`, `docs/adr/0003-policy-valid-time.md`, `docs/adr/0004-versioned-configuration-schemas.md`, `docs/adr/0005-identity-and-sso-foundation.md`, `app/server.py` (all POST endpoints accepting `actor`)

---

## 6. Problem Framing & User Pain (From Plan + Prototype Evidence)

| Pain Point | Current Prototype State | Root Cause | Target Resolution |
|------------|------------------------|------------|-------------------|
| **No reliable audit identity** | Fixed `Demo operator` string; caller-provided `actor` accepted | No authentication/authorization (ADR-0005) | SEC-001: OIDC with validated `iss`+`sub`; SEC-002: RBAC/ABAC |
| **Configuration changes unreviewed** | Change sets require simulation + approval, but actor is untrusted | No identity → no four-eyes enforcement | SEC-001 + SEC-002 + AUD-001 |
| **Bitemporal reconstruction incomplete** | Config + Graph + Requirements + DORA + Controls have time-travel; pre-migration history lost | Migration baseline only; no pre-migration transaction-time | CFG-002 production hardening (P1) |
| **Policy blocks unvalidated** | Controls exist but `validation_status=pending`; enforcement `manual` | No verified primary sources; owners unconfirmed | POL-001/002/003/004 owner confirmation + source reviews |
| **Client requirements unreconciled** | Reconciliation shows `manual_review`/`unmapped`/`configuration_gap` | No config_path mapping; expected_value not linked to schema | CFG-003 parameter ownership + mapping |
| **DORA assessments lack legal force** | `applicability=pending_review`; `criticality=unassessed`; `validity_status=unset_legacy` | Criteria not validated by Compliance/Legal/ICT-risk | POL-004 owner confirmation + criteria validation |
| **No production database** | SQLite file; no encryption, backup, HA, temporal query optimization | Prototype only | P1: PostgreSQL + migration/rollback plan |
| **No secrets management** | None; demo values in code | Prototype only | P1: Secrets manager + rotation |
| **Partner exports unvalidated** | Single `generic-asp-v1.json` profile; no contract tests | Prototype only | P7: EXP-001 contract tests + partner validation |
| **Performance/FactSet integration unverified** | User-supplied names (PA Engine, Analytics API, SPAR) not confirmed | No FactSet tenant access verified | P8: FactSet validation phase 0 |

---

## 7. One-Paragraph Press Release (Synthetic)

> **Atlas Client Configuration Platform** introduces a versioned, bitemporal control plane for institutional client servicing agreements — capturing *what was agreed, when it takes effect, and what was known when*. Starting with a synthetic pilot fonds, the platform models the full manager chain (fiduciary → asset manager → sub-manager → custodian), enforces four-eyes change workflows with simulated fee impact, and maintains append-only audit trails for every configuration, policy, and source review decision. Policy controls for PAI data delivery, Wtp transition milestones, and DORA/ICT classification are registered with explicit human owners, verified primary sources, and graduated enforcement levels — none of which activate as hard blocks until Compliance/Legal and the policy owner co-sign scope, evidence, and exception paths. The system separates valid-time (when a fee or mandate term applies) from transaction-time (when the platform learned it), enabling point-in-time reconstruction for regulators, auditors, and client reporting. All data is synthetic; no production deployment occurs until the identity provider, tenant, role matrix, and policy owners are formally confirmed.

---

## 8. Concise PRD / Discovery Brief

### Problem
Institutional asset owners (pensioenfondsen, verzekeraars, banken) manage complex servicing chains — fiduciary managers, asset managers, sub-managers, custodians — each with contractual fee structures, SLAs, reporting obligations, ESG/SFDR/PAI data requirements, Wtp transition commitments, and DORA/ICT outsourcing classifications. Today these agreements live in documents, spreadsheets, and tribal knowledge. Changes are made without impact simulation, audit trails are incomplete, and compliance controls cannot be enforced because policy ownership, source verification, and enforcement thresholds are undefined.

### Solution (Vertical Slice 1 — Pilot)
A **configuration control plane** that:
1. **Models the pilot chain** — one synthetic fonds + fiduciary + asset manager + sub-manager + custodian with versioned entities, relationships, and service scopes
2. **Versions every configuration** — bitemporal (valid_at × known_at) with append-only snapshots for config, entities, relationships, requirements, DORA assessments, and policies
3. **Enforces change governance** — change sets require simulation (fee impact), four-eyes approval (initiator ≠ approver), and activation with full audit
4. **Registers policy controls** — each with owner, scope, source reference, enforcement level (hard/soft/manual), and a two-step validation workflow (source review → policy decision, different actors)
5. **Reconciles requirements** — client requirements (ESG, SFDR/PAI, Wtp, reporting, costs, chain) map to configuration paths with explicit reconciliation status (match/gap/unmapped/manual)
6. **Exports partner profiles** — versioned, checksummed, audited JSON for downstream consumers
7. **Defers all hard decisions** — identity (ADR-0005), policy owners, legal criteria, FactSet integration — to human owners before production

### Scope (This Discovery Task)
- ✅ Pilot profile definition (synthetic; human selection **OPEN**)
- ✅ First service/manager chain topology (synthetic; human confirmation **OPEN**)
- ✅ Data dictionary across 14 domains (prototype complete; taxonomies **OPEN**)
- ✅ Policy owners identified (prototype placeholders; human assignment **OPEN**)
- ✅ ADR decisions catalogued (4 ADRs; 3 prototype conventions, 1 preparation-only **BLOCKING SEC-001**)
- ✅ Problem framing & user pain mapped
- ✅ Press release + PRD brief authored

### Out of Scope (This Task)
- No implementation code changes
- No real customer data
- No provider/tenant/identity decisions
- No policy owner appointments
- No compliance/legal validation of criteria
- No FactSet verification

### Acceptance Criteria for Discovery Complete
1. [x] Append-only discovery evidence artifact committed in this worktree (`docs/discovery/feature-1-discovery-evidence.md`)
2. [x] Each decision labeled **CONFIRMED** (evidence in repo) or **OPEN** (exact human owner + action needed)
3. [x] Backlog order preserved (Feature 1 → Feature 2 POL-001 → ... → Feature 61 GOV-002) — no reordering
4. [x] Blockers, next agent/action, evidence paths, timestamp reported

### Blockers for Next Phase (Feature 2: POL-001 Besluitenregister)
| Blocker | Owner | Action Required |
|---------|-------|-----------------|
| Policy owner assignment for `CLIENT-PAI-DATA`, `WTP-TRANSITION-DATA`, `ICT-DORA-SCOPE` | Compliance/Legal + Client Service + ICT-risk | Formal appointment with contact, escalation, review cadence |
| Enforcement level definition per control (hard/soft/manual) | Policy owner + Compliance | Document per control with exception process |
| Primary source classification policy | Compliance/Legal | Define what qualifies as `primary_regulatory` vs `customer_contract` vs `customer_policy` |
| Source review → decision actor separation enforcement | Security/Compliance | Confirm SEC-002 role matrix supports this |

### Next Agent / Action
**Independent Reviewer** (profile: `reviewer` or designated human) must review this discovery evidence artifact before Feature 2 (POL-001) can be dispatched. Review should confirm:
- All open decisions are correctly labeled with owners
- No unverified claims promoted to hard controls
- Synthetic data only used
- Backlog gate (Phase 0 exit) criteria understood: "Geen onbekende juridische interpretatie wordt hard afgedwongen; pilotklant en eerste managerketen geselecteerd"

### Evidence Paths (All in Canonical Repo `/Users/ruben/Code/client-config/`)
| Artifact | Path |
|----------|------|
| Project Plan (baseline) | `docs/PROJECT-PLAN.md` |
| ADR-0002 DORA Valid Time | `docs/adr/0002-dora-assessment-valid-time.md` |
| ADR-0003 Policy Valid Time | `docs/adr/0003-policy-valid-time.md` |
| ADR-0004 Config Schemas | `docs/adr/0004-versioned-configuration-schemas.md` |
| ADR-0005 Identity/SSO | `docs/adr/0005-identity-and-sso-foundation.md` |
| Server/API | `app/server.py` |
| Persistence/Logic | `app/store.py` |
| Domain Logic | `app/domain.py` |
| Config Schema v1 | `schemas/configuration-v1.json` |
| API Contracts | `schemas/*.json` |
| UI (Prototype) | `app/static/index.html` |
| SEC-001 Design Notes | `docs/SEC-001-UI-DESIGN-NOTES.md` |
| CFG-002 Design Notes | `docs/CFG-002-UI-DESIGN-NOTES.md` |
| CFG-003 Design Notes | `docs/CFG-003-UI-DESIGN-NOTES.md` |

### Timestamp
**Discovery Completed:** 2026-11-04T09:15:00+01:00
**Next Review Gate:** Independent Reviewer sign-off on this artifact
**Task Status:** `ready for review` → `kanban_request_review` pending