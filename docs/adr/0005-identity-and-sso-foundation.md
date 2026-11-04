# ADR-0005: Identity and SSO foundation

- **Status:** Accepted for preparation; identity provider selection remains open
- **Date:** 2026-11-03
- **Scope:** SEC-001 real identity and SSO foundation

## Context

The prototype currently displays a fixed `Demo operator` identity. API mutations accept actor strings from browser requests. Neither value proves who initiated an action, and the application does not enforce authentication or authorization. This is acceptable only for the synthetic local prototype and must not be represented as production access control.

The project plan names Microsoft Entra ID or a confirmed enterprise SSO provider, but no tenant, identity owner, provider, environment, or role mapping has been confirmed. Selecting those details without the identity owner would create an unsupported security and operational decision.

## Decision

Proceed with design and implementation preparation only. Do not implement a login flow, create local users, infer roles from email or group names, accept identity headers, or label the prototype authenticated. Keep provider selection open for the identity/platform owner.

Prepare a provider-neutral OpenID Connect authorization-code integration for a confidential server-side web application. Before implementation, the application must be adapted to use an established OIDC client library rather than hand-written token validation. The selected provider and deployment must be checked for the required protocol behavior and configuration.

## Security invariants for the later implementation

1. The server is the OAuth/OIDC client; secrets and tokens stay server-side. Do not store tokens or session credentials in browser storage.
2. Use authorization code flow with PKCE (`S256`), a one-time state bound to the browser session, and a transaction-specific OIDC nonce.
3. Validate the ID token signature and permitted algorithm, issuer, audience, expiry, nonce, and key provenance against the configured issuer metadata/JWKS. Reject mismatches and unknown issuers. Do not trust user-supplied identity or role fields.
4. Use exact, allow-listed redirect URIs and prevent open redirects. Require HTTPS outside local development.
5. Issue an opaque server-side session with a `Secure`, `HttpOnly`, appropriately `SameSite` cookie; rotate the session on authentication and privilege changes, enforce idle/absolute expiry, and invalidate it on logout.
6. Protect state-changing requests against CSRF. Do not treat CORS, a hidden UI control, or a caller-provided `actor` field as authorization.
7. Derive the audit actor from a stable, issuer-qualified subject (`iss` + `sub`). Keep display name and email as descriptive claims only. Record the authenticated actor and authorization decision server-side.
8. If identity or session validation is unavailable, fail closed for protected routes. Keep health/readiness behavior explicitly separated from authenticated business APIs.

These are implementation requirements, not a claim that the current prototype meets them. OAuth security guidance identifies PKCE and transaction-bound protections as important controls; OIDC requires exact issuer and audience validation. See [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html) and [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html).

## Preparation deliverables

- Identity provider and tenant/environment owner confirmed by the platform/identity owner.
- Provider discovery URL, client registration, exact callback/logout URLs, supported signing algorithms, key rotation behavior, and test tenant documented. Secrets must be provisioned through the deployment secret manager and must not enter Git.
- Stable subject claim and any immutable tenant/organization claim mapped to the internal actor identifier.
- SEC-002 role/capability matrix approved by the product owner and security owner; group/role claim mapping and access review process documented.
- Migration inventory identifies every API mutation that currently accepts an actor string. All must derive actor context from the authenticated request.
- Session store, cookie domain, TLS termination, reverse-proxy trust boundaries, logout behavior, recovery, monitoring, and operational ownership documented.
- Synthetic test identities and a non-production identity environment available. No real customer or financial data in fixtures.

## Acceptance criteria for SEC-001 implementation

- Anonymous requests cannot read or mutate protected business APIs; the intended unauthenticated routes are explicitly listed and reviewed.
- Successful sign-in creates a server-side session and displays an identity derived from the validated provider subject.
- Invalid state, nonce, signature, issuer, audience, expiry, redirect URI, and session are rejected without exposing tokens or secrets in responses/logs.
- Session rotation, expiry, logout invalidation, and CSRF protection are verified.
- Audit actor values come from the validated session, and caller-provided actor values cannot impersonate another actor.
- Provider outage fails closed for protected routes, with a safe operator-facing error and useful redacted server logs.
- SSO and actor attribution pass browser and API acceptance checks in a non-production tenant before the SEC-001 implementation is marked complete.

## Consequences

- SEC-001 remains open until provider selection, deployment details, and identity ownership are confirmed and the implementation criteria pass.
- SEC-002 authorization is a separate follow-up. Authentication alone must not grant broad access.
- The current demo remains unauthenticated and must only use synthetic data. Its actor strings are demo inputs, not reliable audit identity.

## Deferred decisions

- Microsoft Entra ID versus another enterprise OIDC provider.
- Tenant, application registration ownership, environments, client authentication method, and secret rotation owner.
- Internal immutable actor key and any tenant boundary model.
- Role/capability assignments, privileged role workflow, and access review cadence (SEC-002).
- Hosting/session store and production TLS/reverse-proxy topology.
