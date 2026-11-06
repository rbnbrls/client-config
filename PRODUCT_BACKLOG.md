# Client Configuration Platform — Hermes Product Backlog

**Canonical backlog:** `/Users/ruben/Code/client-config/PRODUCT_BACKLOG.md`
**Audience:** Hermes lead, Builder, Reviewer and release-gate workers
**Repository:** `rbnbrls/client-config`
**Code baseline audited:** `ec23d47` (`main`, 2026-11-06)
**Execution rule:** one feature at a time, one active Builder or Reviewer, linear dependency chain, green evidence before the next feature becomes ready.

## 1. How Hermes must read this file

The hierarchy is deliberately fixed:

`Feature` → `Slice` → `User story` → `Acceptance evidence` → `Gate`

- **Feature** is a product capability area (`P0`–`P8`).
- **Slice** is one independently implementable backlog item with a stable ID (`F01`, `POL-001`, etc.). In this repository the numbered `F01`–`F62` sequence is the execution order.
- **User story** states the outcome from the perspective of the configuration owner, reviewer or operator. It is not permission to infer missing legal, customer or supplier decisions.
- **Acceptance evidence** is the test/evidence path that a Reviewer must read back. A document named `*-evidence.md` is historical evidence, not proof of production readiness.
- **Gate** is the remaining human, technical or external decision that must be cleared before the slice can be promoted.

### Status vocabulary

| Status | Meaning for Hermes |
|---|---|
| `prototype-done` | Code, focused tests and evidence exist in this checkout. It is eligible for review, not production release. |
| `prototype-partial` | A demonstrator or readiness flow exists, but the contracted capability is incomplete. |
| `blocked` | Work cannot safely proceed without a named external decision; do not implement an assumption. |
| `planned` | No implementation evidence exists in the audited checkout. |
| `released` | Not currently used. No slice in this backlog is production-released. |

### Non-negotiable repository rules

- Use synthetic customer, financial and partner data only.
- Configuration, policy, schemas, evidence references and exports are append-only; preserve valid time and transaction time where applicable.
- Shared domain functions must be used by production paths and twin/simulation paths.
- Version API contracts, parameter schemas, policy rules and partner export profiles.
- Audit actor, reason, evidence, approval, simulation and publication/export state.
- A compliance claim without validated evidence is `te valideren door Compliance/Legal` and must not become a hard block.
- DORA and non-ICT asset-management outsourcing remain separate classifications.
- A blocking policy requires owner, source, scope, exception process and acceptance criteria.

## 2. Current product state

The repository is a local standard-library Python prototype using SQLite. The code has append-only/versioned stores and focused tests for F01–F51. The UI is a multi-persona workflow workbench covering the customer journey from prospect and sales through onboarding and daily service. All capabilities are intentionally visible during development; later releases may distribute them through persona-specific views and authorization. It is not an authenticated production control environment.

### Customer-journey workbench

| Journey phase | Collaborative outcome | Initial persona labels in the GUI |
|---|---|---|
| Prospect & sales | Capture prospect context, proposal, pricing and intended service scope before commitment. | Sales, Fee |
| Onboarden als klant | Turn the agreed relationship into customer, mandate, requirements, chain, outsourcing and policy configuration. | Accountmanager, Legal, Operations, Risk, Compliance |
| Dagelijkse klantbediening | Review the live customer relationship, manage changes, evidence decisions and share controlled exports. | Accountmanager, Operations, Reviewer, Partner |
| Platform & governance | Manage identity, schemas, discovery decisions and technical governance that support every journey phase. | Platform, Security, Data, Product, Legal |

The GUI labels are collaboration hints, not authorization. Persona-specific navigation, permissions and approval separation are later slices under SEC-001/SEC-002 and must not be inferred from the labels.

### Code-backed inventory

| Area | Evidence in code | Current interpretation |
|---|---|---|
| HTTP/API | `app/server.py` | Health/build-info, customer/configuration, policy, discovery, chain, DORA, graph, validation, change, simulation, approval, activation and export paths exist. Several later domain stores are test-backed but not yet exposed as complete UI/API workflows. |
| Domain logic | `app/domain.py` | Shared fee, FX, rounding, tier, cap/floor and performance-fee primitives exist. |
| Persistence | `app/store.py` | Append-only/versioned tables, audit, temporal reads and domain stores exist for the prototype slices. SQLite is not production storage. |
| Schema validation | `app/config_schema.py` | Versioned typed configuration schemas and validation exist. |
| Frontend | `app/static/index.html`, `app/static/discovery-workbench.js`, `app/static/institutional-theme.css` | Dashboard and F01 discovery UI exist. The browser flow is local and uses demo identity. |
| Tests | `tests/test_*.py` | Focused test files exist for F01–F51. Full-suite evidence is historical and must be rerun by the active Reviewer after changes. |
| Evidence | `docs/feature-*-evidence.md`, `docs/discovery/feature-1-discovery-evidence.md` | Prototype acceptance and prior review evidence; each new run must record exact commit, commands and result. |

### Release truth

No feature is production-ready. The principal release blockers are real identity/SSO and RBAC, production persistence/retention/backup, formal role and policy ownership, Compliance/Legal validation, customer/partner decisions, integration contracts, observability and operational recovery.

## 3. Execution queue

The queue is strictly serial. `Ready` means the dependency and decision gate are clear; it does not mean the item is already implemented.

| Order | Slice | Phase | Status | Dependency | Next Hermes action |
|---:|---|---|---|---|---|
| 1 | F01 / Discovery | P0 | `prototype-done` | — | Reviewer read-back of discovery decisions; clear pilot and owner gates. |
| 2–8 | POL-001…POL-004, CFG-001…CFG-003 | P0–P1 | `prototype-done` | F01 → previous slice | Review current evidence; keep unvalidated policy signals non-blocking. |
| 9 | SEC-001 | P1 | `prototype-partial` + `blocked` | F08 | Obtain provider, tenant, identity owner, deployment and claim-mapping decision. |
| 10–12 | SEC-002, AUD-001, DOC-001 | P1 | F10 `prototype-done`; F11–F12 `prototype-done` | previous slice | Promote only after real identity and role matrix are approved. |
| 13–19 | OUT-001…OUT-007 | P2 | `prototype-done` | F12 → previous slice | Review customer-specific outsourcing and ICT classification gates. |
| 20–25 | ESG-001…ESG-006 | P3 | `prototype-done` | F19 → previous slice | Review customer policy, OESO/UNGP, methodology and exception ownership. |
| 26–31 | RPT-001…RPT-006 | P4 | `prototype-done` | F25 → previous slice | Review SFDR/PAI applicability, data owners and disclosure permissions. |
| 32–36 | WTP-001…WTP-005 | P5 | `prototype-done` | F31 → previous slice | Review fund-specific Wtp responsibilities, dates and evidence. |
| 37–41 | FEE-001…FEE-005 | P6 | `prototype-done` | F36 → previous slice | Review fee contracts and shared calculation golden masters. |
| 42–47 | TWIN-001…TWIN-003, EXP-001…EXP-002, INT-001 | P7 | `prototype-done` | F41 → previous slice | Confirm partner contract, source systems, privacy and integration ownership. |
| 48–51 | PERF-001…PERF-002, BENCH-001…BENCH-002 | P8 | `prototype-done` | F47 → previous slice | Reviewer rerun; keep method/benchmark choices customer-specific. |
| 52 | BENCH-003 | P8 | `planned` | F51 | First next implementation slice; requires calendar, cutoff and proxy decisions. |
| 53–62 | PORT-001…PORT-003, CALC-001…CALC-003, BI-001…BI-002, GOV-001…GOV-002 | P8 | `planned` | F52 → previous slice | Do not start until F52 is reviewed green and platform/engine decisions are recorded. |

## 4. Feature and slice contracts

Each row below is the canonical Hermes task contract. Evidence paths are relative to the repository root.

### Feature P0 — Discovery and policy governance

| Slice | User story | Acceptance contract | Status / evidence | Gate |
|---|---|---|---|---|
| **F01** Discovery | As a product owner, I want pilot profile, first chain, data dictionary, policy owners and open ADR decisions captured so implementation does not encode assumptions. | Catalog is explicit about open/synthetic decisions; decision writes are append-only and audited; UI/API can read and save a decision. | `prototype-done`; `app/static/discovery-workbench.js`, `tests/test_discovery_workbench.py`, `docs/discovery/feature-1-discovery-evidence.md`. | Pilot customer, chain, owners and ADR decisions still require human confirmation. |
| **F02 / POL-001** Decisions register | As a policy owner, I want a versioned control decision with owner, scope, source, applicability and enforcement so only approved rules can block. | Required contract fields; append-only history; hard block refused without validated status and evidence. | `prototype-done`; `tests/test_policy_register.py`, `docs/feature-2-pol001-evidence.md`. | Formal policy owners and authority model. |
| **F03 / POL-002** Source control | As a reviewer, I want source reviews separated from policy decisions so evidence quality and independence are visible. | Verified primary/customer source required; reviewer differs from decision actor; later review can return status to pending. | `prototype-done`; `tests/test_policy_register.py`, `docs/feature-3-pol002-evidence.md`. | Compliance/Legal validates source classification and retention. |
| **F04 / POL-003** Customer variants | As a customer owner, I want mandate-specific requirements and reconciliation states so a match is not mistaken for compliance. | Versioned requirements, explicit mapping and non-blocking `configured_match`, `configuration_gap`, `unmapped` or `manual_review`. | `prototype-done`; `tests/test_client_variants.py`; evidence is contained in feature/phase merge records. | Contract interpretation and customer mapping approval. |
| **F05 / POL-004** DORA classification | As a risk reviewer, I want asset-management, third-party ICT and own-platform ICT assessments separated. | Append-only human assessment with scope, applicability, criticality, source, reviewer and review date; no legal algorithm. | `prototype-done`; `tests/test_dora_assessments.py`, `tests/test_ict_provider_relations.py`. | Compliance/Legal and ICT-risk criteria. |

### Feature P1 — Configuration, security, audit and evidence

| Slice | User story | Acceptance contract | Status / evidence | Gate |
|---|---|---|---|---|
| **F06 / CFG-001** Entities and relations | As an operations owner, I want versioned customer/fund/party/service relationships so the active chain is reconstructable. | Allowed entity/relationship types, same-customer scope, append-only versions and temporal graph reads. | `prototype-done`; `tests/test_entities_relations.py`, `docs/feature-6-cfg001-evidence.md`. | Production authorization and full temporal migration. |
| **F07 / CFG-002** Bitemporal revisions | As an auditor, I want valid-time and transaction-time reads so I can distinguish what applied from what was known. | Historical reads for configuration, graph, requirements, DORA and policy; update/delete blocked. | `prototype-done`; `tests/test_policy_bitemporal.py`, `docs/feature-7-cfg-002-evidence.md`. | Production retention, immutability and pre-migration history. |
| **F08 / CFG-003** Typed parameters | As a configuration owner, I want versioned schemas and server-side validation so invalid values cannot enter the control plane. | Typed parameter definitions, historical schema selection, validation fingerprint and append-only schema records. | `prototype-done`; `tests/test_config_schema.py`, `docs/feature-8-cfg-003-evidence.md`. | Formal schema owners and customer-specific norms. |
| **F09 / SEC-001** Identity and SSO | As a security owner, I want real identity claims and tenant-bound authentication so actor fields are trustworthy. | Implement OIDC/Entra only after provider, tenant, deployment, app registration, secret handling and claim mapping are approved. | `prototype-partial` / `blocked`; readiness evidence in `docs/feature-9-sec-001-evidence.md`; no production auth. | **Human gate:** identity owner decision. Demo actor is not authentication. |
| **F10 / SEC-002** Authorization and separation | As an approver, I want role-based separation so an initiator cannot approve their own change. | Approved role matrix, authorization checks, approval separation and review evidence. | `prototype-done` prototype; `tests/test_audit_append_only.py`, `docs/feature-10-sec-002-evidence.md`. | Production identity, role matrix and access review. |
| **F11 / AUD-001** Audit | As an auditor, I want immutable change evidence so actor, reason, approval, simulation and publication are traceable. | Append-only audit; rich records; update/delete blocked; lifecycle fields retained. | `prototype-done`; `tests/test_audit_append_only.py`, `docs/feature-11-aud-001-evidence.md`. | Production immutability, access controls and retention. |
| **F12 / DOC-001** Evidence references | As a reviewer, I want version-bound document metadata without inline document content. | Reference subject/version, confidentiality, retention and audit metadata; no inline content; append-only. | `prototype-done`; `tests/test_document_references.py`, `docs/feature-12-doc-001-evidence.md`. | Secure document store, retention and access policy. |

### Feature P2 — Outsourcing and chain control

| Slice | User story | Acceptance contract | Status / evidence |
|---|---|---|---|
| **F13 / OUT-001** Activity register | As an outsourcing owner, I want activities, scope, service and contract period recorded per relation. | Required fields, versioning, append-only and temporal reads. | `prototype-done`; `tests/test_activity_register.py`, `docs/feature-13-out-001-evidence.md`. |
| **F14 / OUT-002** Chain register | As a risk reviewer, I want direct and indirect parties traced so impacted mandates are known. | Parent/child validation, cycle prevention, trace and impact queries. | `prototype-done`; `tests/test_chain_register.py`, `docs/feature-14-out-002-evidence.md`. |
| **F15 / OUT-003** Contract minimums | As a contract owner, I want required outsourcing clauses and missing fields visible. | Versioned minimum fields, missing-field result and customer scope. | `prototype-done`; `tests/test_contract_minimums.py`, `docs/feature-15-out-003-evidence.md`. |
| **F16 / OUT-004** Selection assessment | As a selection reviewer, I want customer-specific criteria and evidence reviewed periodically. | Criteria, missing list, review status and append-only assessment. | `prototype-done`; `tests/test_selection_assessment.py`, `docs/feature-16-out-004-evidence.md`. |
| **F17 / OUT-005** Notification signals | As an operations owner, I want onboarding and material changes to create owned review tasks. | Signal trigger/status, owner and deadline required for review; no automatic DNB submission. | `prototype-done`; `tests/test_notification_signals.py`, `docs/feature-17-out-005-evidence.md`. |
| **F18 / OUT-006** ICT separation | As an ICT-risk owner, I want ICT provider relations separate from asset-management outsourcing. | Distinct classification, provider/service relation and temporal append-only records. | `prototype-done`; `tests/test_ict_provider_relations.py`, `docs/feature-18-out-006-evidence.md`. |
| **F19 / OUT-007** Governance | As a fund owner, I want monitoring, escalation, capacity and independent review recorded. | Governance policy with applicability, reviewer, validity and audit. | `prototype-done`; `tests/test_governance_policies.py`, `docs/feature-19-out-007-evidence.md`. |

### Feature P3 — ESG and manager lifecycle

| Slice | User story | Acceptance contract | Status / evidence |
|---|---|---|---|
| **F20 / ESG-001** Policy profile | As a mandate owner, I want customer-specific ESG policy and scope versioned. | In-force mandate profile overrides fund default; validity and source evidence visible. | `prototype-done`; `tests/test_esg_policy_profiles.py`, `docs/feature-20-esg-001-evidence.md`. |
| **F21 / ESG-002** Manager selection | As a selection reviewer, I want criteria, exceptions and review stages recorded per manager. | Customer-specific criteria; exceptions require rationale, approver and end date. | `prototype-done`; `tests/test_esg_manager_selections.py`, `docs/feature-21-esg-002-evidence.md`. |
| **F22 / ESG-003** Contractual flow-down | As a contract owner, I want ESG clauses flowed to managers and submanagers. | Target/clause enum, submanager flow-down, versioning and controlled exceptions. | `prototype-done`; `tests/test_esg_contractual_flowdowns.py`, `docs/feature-22-esg-003-evidence.md`. |
| **F23 / ESG-004** Due diligence | As a due-diligence reviewer, I want findings, human judgement, owner and deadline tracked. | Workflow steps, priority, deadline and exception validation. | `prototype-done`; `tests/test_esg_due_diligence_dossiers.py`, `docs/feature-23-esg-004-evidence.md`. |
| **F24 / ESG-005** Engagement/incidents | As a stewardship owner, I want incident source, engagement, remedy and closure recorded. | Severity/progress/retention states and append-only history. | `prototype-done`; `tests/test_esg_engagement_incidents.py`, `docs/feature-24-esg-005-evidence.md`. |
| **F25 / ESG-006** Periodic review | As a manager reviewer, I want scheduled review and escalation for deviations. | Review period, deviation rationale, escalation and end date where required. | `prototype-done`; `tests/test_esg_periodic_reviews.py`, `docs/feature-25-esg-006-evidence.md`. |

### Feature P4 — Reporting, SFDR/PAI and transparency

| Slice | User story | Acceptance contract | Status / evidence |
|---|---|---|---|
| **F26 / RPT-001** Reporting catalog | As a reporting owner, I want each metric, perimeter, deadline and recipient defined. | Versioned report type, metric, frequency, language and recipients. | `prototype-done`; `tests/test_reporting_catalog.py`, `docs/feature-26-rpt-001-evidence.md`. |
| **F27 / RPT-002** Data delivery | As a data owner, I want each field linked to supplier, channel, period and validation. | Versioned delivery agreement and query filters. | `prototype-done`; `tests/test_data_delivery_agreements.py`, `docs/feature-27-rpt-002-evidence.md`. |
| **F28 / RPT-003** SFDR/PAI profile | As a compliance reviewer, I want applicable indicators and responsibility configured per customer. | Versioned profile; no universal applicability assumption. | `prototype-done`; `tests/test_sfdr_pai_profiles.py`, `docs/feature-28-rpt-003-evidence.md`. |
| **F29 / RPT-004** Comply-or-explain | As a policy owner, I want deviations explained, approved and followed up. | Status enum, rationale, impact, approval and follow-up are versioned. | `prototype-done`; `tests/test_comply_or_explain.py`, `docs/feature-29-rpt-004-evidence.md`. |
| **F30 / RPT-005** Execution | As a reporting operator, I want completeness, delay, error, recovery and approval visible. | Execution lifecycle with delivery status and escalation. | `prototype-done`; `tests/test_reporting_executions.py`, `docs/feature-30-rpt-005-evidence.md`. |
| **F31 / RPT-006** Transparency output | As a disclosure owner, I want consent and confidentiality checked before output. | Disclosure permission, confidentiality and append-only output record. | `prototype-done`; `tests/test_transparency_outputs.py`, `docs/feature-31-rpt-006-evidence.md`. |

### Feature P5 — Wtp transition

| Slice | User story | Acceptance contract | Status / evidence |
|---|---|---|---|
| **F32 / WTP-001** Transition profile | As a transition owner, I want phase, dates, scope and owner configured per fund. | Required phase/owner fields, dates and versioning. | `prototype-done`; `tests/test_wtp_transition_profiles.py`, `docs/feature-32-wtp-001-evidence.md`. |
| **F33 / WTP-002** RACI | As a transition coordinator, I want party roles, handoffs and escalation visible. | Party-role enum, dependencies and query filters. | `prototype-done`; `tests/test_wtp_raci_dependencies.py`, `docs/feature-33-wtp-002-evidence.md`. |
| **F34 / WTP-003** Transition data | As a data owner, I want data for/before/after transition validated and reconciled. | Data-phase enum, ownership, validation and append-only versions. | `prototype-done`; `tests/test_wtp_transition_data.py`, `docs/feature-34-wtp-003-evidence.md`. |
| **F35 / WTP-004** Milestones | As a go/no-go reviewer, I want deliverables, evidence and readiness status tracked. | Milestone/evidence status and query filters. | `prototype-done`; `tests/test_wtp_milestones.py`, `docs/feature-35-wtp-004-evidence.md`. |
| **F36 / WTP-005** Risks | As a transition risk owner, I want risks, controls and evidence status versioned. | Risk category, evidence status and append-only history. | `prototype-done`; `tests/test_wtp_risks.py`, `docs/feature-36-wtp-005-evidence.md`. |

### Feature P6 — Fees, costs and simulation

| Slice | User story | Acceptance contract | Status / evidence |
|---|---|---|---|
| **F37 / FEE-001** Components | As a fee owner, I want contract fee components, tiers, minimums, discounts and currencies configured. | Fee-type, currency, frequencies, performance-fee, side-letter, indexation and append-only tests. | `prototype-done`; `tests/test_fee_components.py`, `docs/feature-37-fee-001-evidence.md`. |
| **F38 / FEE-002** Calculation rules | As a calculation owner, I want versioned rules for base, period, valuation, rounding and FX. | Rule schema and export; shared functions in `app/domain.py`. | `prototype-done`; `tests/test_fee_calculation_rules.py`, `docs/feature-38-fee-002-evidence.md`. |
| **F39 / FEE-003** Cost overview | As a client owner, I want direct and other agreed costs allocated and exportable. | Cost type, currency, perimeter, allocation, performance fee and export. | `prototype-done`; `tests/test_cost_overview.py`, `docs/feature-39-fee-003-evidence.md`. |
| **F40 / FEE-004** Manager look-through | As a transparency owner, I want manager/vehicle coverage and disclosure permission visible. | Manager, fund, mandate, coverage and permission are versioned/exportable. | `prototype-done`; `tests/test_manager_look_through.py`, `docs/feature-40-fee-004-evidence.md`. |
| **F41 / FEE-005** Simulation | As a scenario owner, I want baseline/scenario fee deltas reproducibly calculated. | Level filters, append-only scenario records, export and shared domain calculation. | `prototype-done`; `tests/test_fee_simulation.py`, `docs/feature-41-fee-005-evidence.md`. |

### Feature P7 — Twin, exports and integrations

| Slice | User story | Acceptance contract | Status / evidence |
|---|---|---|---|
| **F42 / TWIN-001** Change-as-code | As an implementer, I want a declarative change with base, effective date, reason and versions. | Required fields, append-only versions and export. | `prototype-done`; `tests/test_change_as_code.py`, `docs/feature-42-twin-001-evidence.md`. |
| **F43 / TWIN-002** Scenario snapshot | As a reviewer, I want an isolated immutable snapshot so simulation cannot write production. | Snapshot inputs, reproducibility, versioning and export. | `prototype-done`; `tests/test_scenario_snapshots.py`, `docs/feature-43-twin-002-evidence.md`. |
| **F44 / TWIN-003** Impact analysis | As a change owner, I want baseline/scenario impact across domains and dependencies. | Reproducible impact result, filters and export. | `prototype-done`; `tests/test_impact_analysis.py`, `docs/feature-44-twin-003-evidence.md`. |
| **F45 / EXP-001** Partner profiles | As an integration owner, I want versioned mappings, privacy classification and contract tests. | Mapping type checks, non-empty classification/privacy, reproducible export. | `prototype-done`; `tests/test_partner_profiles.py`, `docs/feature-45-exp-001-evidence.md`. |
| **F46 / EXP-002** Publication status | As a publisher, I want export identity, checksum, target and receipt status auditable. | Versioned publication status and export. | `prototype-done`; `tests/test_publication_status.py`, `docs/feature-46-exp-002-evidence.md`. |
| **F47 / INT-001** Integrations | As an integration operator, I want source, direction, delivery and reconciliation status tracked. | Integration and delivery are append-only, versioned and exportable. | `prototype-done`; `tests/test_integrations.py`, `docs/feature-47-int-001-evidence.md`. |

### Feature P8 — Performance, benchmarks and reporting pipeline

| Slice | User story | Acceptance contract | Status / evidence | Gate |
|---|---|---|---|---|
| **F48 / PERF-001** Method profile | As a mandate owner, I want return method and conventions versioned per mandate. | Method/valuation/cashflow/FX/fee conventions are explicit and exportable. | `prototype-done`; `docs/feature-48-perf-001-evidence.md`. | Customer/mandate method approval. |
| **F49 / PERF-002** Pension portfolios | As a pension reporting owner, I want return and matching/LDI portfolios separated with agreed indicators. | Portfolio type and pension indicators are versioned/exportable. | `prototype-done`; `docs/feature-49-perf-002-evidence.md`. | Fund-specific LDI and hedge definitions. |
| **F50 / BENCH-001** Benchmark definition | As a performance owner, I want index type, currency, hedge and composite weights versioned. | Benchmark definitions, components and export; append-only history. | `prototype-done`; `docs/feature-50-bench-001-evidence.md`. | Benchmark provider and customer convention. |
| **F51 / BENCH-002** Benchmark history | As an auditor, I want effective and known-at moments plus history policy preserved. | Bitemporal reads, explicit history policy, append-only update/delete protection and export. | `prototype-done`; `tests/test_bench_002.py`, `docs/feature-51-bench-002-evidence.md`. | Reviewer rerun after current baseline. |
| **F52 / BENCH-003** Availability and timing | As a performance operator, I want market calendar, cutoff, frequency and approved proxy status visible. | Calendar/cutoff/proxy rule has source, status flag, period and no false finality. | `planned`; no matching implementation/test/evidence in audited checkout. | Customer decision on calendars, cutoffs and proxy policy. |
| **F53 / PORT-001** Identifiers and hierarchy | As a data steward, I want fund→client→mandate→portfolio→manager mappings versioned. | Internal/external identifiers and hierarchy are auditable. | `planned`; no matching implementation/test/evidence. | External source codes and owner. |
| **F54 / PORT-002** Input contract | As a data owner, I want positions, trades, cashflows, corporate actions, accruals and fees governed by source/schema/as-of. | Versioned input schema and provenance contract. | `planned`; no matching implementation/test/evidence. | Custodian/source contract. |
| **F55 / PORT-003** Data quality/corrections | As a data-quality operator, I want reconciliation, stale/missing checks and corrections as new versions. | Quality status, correction lineage and provisional/final state. | `planned`; no matching implementation/test/evidence. | Custodian reconciliation policy. |
| **F56 / CALC-001** Calculation/attribution profile | As a performance owner, I want engine, request fields and attribution method configured only after the engine is confirmed. | Versioned calculation/attribution profile; no invented FactSet endpoint contract. | `planned`; no matching implementation/test/evidence. | FactSet/engine, license and method decision. |
| **F57 / CALC-002** Traceable run | As an auditor, I want request, raw response, source references, versions and status tied to one run. | Immutable run reference and bronze/silver/gold links/checksums where approved. | `planned`; no matching implementation/test/evidence. | Storage, privacy and retention decision. |
| **F58 / CALC-003** Orchestration | As an operator, I want idempotent, retryable runs after prices and FX are ready. | Run IDs, retry/rate-limit state and controlled authentication. | `planned`; no matching implementation/test/evidence. | ADF/Fabric/platform decision. |
| **F59 / BI-001** Power BI model | As a reporting analyst, I want one governed facts/dimensions model with central calculations. | Daily performance, attribution and allocation facts; portfolio, date, client, benchmark, asset class, currency and version dimensions. | `planned`; no matching implementation/test/evidence. | Semantic model and calculation ownership. |
| **F60 / BI-002** Dashboard and access | As a client user, I want approved performance views with tenant/client isolation. | Periods, excess return, attribution, tracking metrics, allocation, update status and RLS evidence. | `planned`; no matching implementation/test/evidence. | Entra/RLS/guest or embedded access decision. |
| **F61 / GOV-001** Indicative vs official | As a reporting approver, I want provisional numbers separated from locked official results. | Review/approval, lock, correction and restatement are versioned. | `planned`; no matching implementation/test/evidence. | Official calendar and approval policy. |
| **F62 / GOV-002** Method document | As a client reviewer, I want an approved method note export per mandate. | Export method, valuation, cashflow, FX, benchmark, attribution, periods, source, status and change history. | `planned`; no matching implementation/test/evidence. | Mandate approval and reporting contract. |

## 5. Cross-cutting slices and release gates

These are release gates, not hidden extra features. They apply to every slice and must be checked by the Reviewer:

1. **Data safety:** synthetic fixtures only; no customer identifiers, secrets or production exports.
2. **Temporal integrity:** append-only writes; valid time and transaction time preserved where the domain requires them.
3. **Auditability:** actor, reason, evidence, approval, simulation and publication/export status present or explicitly marked not applicable.
4. **Policy safety:** unvalidated legal/customer interpretations remain non-blocking and carry `te valideren door Compliance/Legal`.
5. **Contracts:** API, schema, policy and partner profile versions are explicit and testable.
6. **Shared logic:** fee and simulation calculations call the same domain functions.
7. **Security:** demo identity is never described as authentication; SEC-001 and SEC-002 gates are separate.
8. **Operations:** logs contain no sensitive values; error states, retries, exports and deadlines are observable.
9. **Recovery:** production promotion requires backup/restore, retention, RTO/RPO and migration evidence.
10. **Browser/UI:** frontend changes retain the established design notes, accessible targets and a browser smoke check.

## 6. Open decision register

| Decision | Owner required | Blocks |
|---|---|---|
| Pilot customer/fund, first chain and partner export | Product + customer owner | F01 promotion and partner slices |
| Policy owners, Compliance/Legal reviewers and exception authority | Product + Compliance/Legal | Any hard policy block |
| Identity provider, tenant, deployment, app registration and claim mapping | Identity owner | F09/F10 production promotion |
| Role matrix, four-eyes and access-review cadence | Security + business owner | F10 production promotion |
| Production database, immutability, retention, backup and RTO/RPO | Platform owner | P1 release gate |
| DORA/non-ICT applicability and criticality criteria | Compliance/Legal + ICT risk | F05/F18 production use |
| Customer-specific ESG, SFDR/PAI, Wtp and outsourcing obligations | Customer owner + Compliance/Legal | P2–P5 hard controls |
| Fee contract, calculation conventions and look-through perimeter | Client/fee owner | P6 official outputs |
| Performance engine, FactSet tenant/licence/API and method conventions | Performance/platform owner | F56 onward |
| Calendar, cutoff, proxy and benchmark history policy | Performance owner + customer | F52 onward |
| ADLS zones/retention, orchestration, Power BI model and RLS | Data/platform/security owners | F57–F60 |

Until a decision is recorded with actor, reason, evidence and approval, Hermes must create a decision task or non-blocking signal, not a universal default.

## 7. Reviewer protocol

For each slice:

1. Read the dependency and open-decision row above.
2. Inspect the referenced implementation, test and evidence files at the exact commit.
3. Run the focused test file and the relevant regression suite.
4. Check append-only behavior, synthetic data, temporal semantics and audit fields.
5. For UI/API slices, perform the local browser/HTTP smoke test and record the URL/build ID.
6. Return one verdict: `APPROVED`, `CHANGES REQUESTED` or `BLOCKED — decision required`.
7. Only `APPROVED` moves the next slice to `Ready`.

Historical GitHub/Hermes sync metadata is intentionally not duplicated here. Hermes should mirror this file into its board and retain task IDs, worker outputs and verdicts on the board item; this repository file remains the product contract and current-state source.
