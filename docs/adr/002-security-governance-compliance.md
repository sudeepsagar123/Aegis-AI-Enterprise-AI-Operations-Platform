# ADR-002: Enterprise Security, RBAC Governance & Compliance Framework

- **Status**: Accepted
- **Decider**: Architecture Steering Committee
- **Date**: 2026-08-04

---

## Context & Problem Statement

Aegis AI is designed as a mission-critical AI operations platform for enterprise environments. Because AI agents are granted access to write to and execute actions on infrastructure (e.g. Jira issue generation, database queries, deployment triggering, Slack notifications), the platform must guarantee zero unauthorized access, immutability of system actions, and strict compliance with standards like **SOC 2 Type II**, **HIPAA**, and **GDPR**.

Specifically, we needed to address:
1. Fine-grained RBAC with deterministic permission checks.
2. Safe password storage resilient to algorithm truncation vulnerabilities.
3. Immutability of audit records for security auditing.
4. Response header hardening and transport layer security.
5. Human-In-The-Loop approval gates for high-risk autonomous agent operations.

---

## Decision Drivers

* **SOC 2 Compliance**: Mandatory append-only audit trail with request correlation context.
* **Least Privilege Principle**: Users and service accounts must only hold minimum required permissions.
* **Defense in Depth**: Security controls active at API edge, middleware, model context, and database layers.
* **Audit Transparency**: Clear visibility into which agent/user executed an action and why.

---

## Considered Options

1. **Basic OAuth 2.0 Scope Matching**: Lightweight, but lacks fine-grained hierarchical role permissions.
2. **External Identity Provider Only (Okta/Auth0)**: Offloads authentication, but still requires local RBAC and fine-grained permissions evaluation.
3. **Hybrid Enterprise RBAC + Custom Security Middleware (Chosen)**: Local JWT token authentication, 6-role / 21-permission matrix, native `bcrypt` hashing, `SecurityHeadersMiddleware`, and human-in-the-loop approval gates.

---

## Decision Outcome

**Chosen Option**: Option 3 (Hybrid Enterprise RBAC + Custom Security Middleware).

### Key Architectural Standards Implemented:

1. **Password Hashing Security**:
   - Standardized on native `bcrypt` directly (bypassing `passlib` to mitigate Python 3.13 length truncation issues).
   - Enforced maximum password input length of 72 bytes before hash calculation.

2. **Role & Permission Hierarchy (6 Roles, 21 Permissions)**:
   - `super_admin`: System management, organization configuration, full access.
   - `org_admin`: Organization-level settings and user management.
   - `incident_manager`: Incident lifecycle control, team assignment.
   - `operator`: Autonomous agent execution, incident response.
   - `viewer`: Read-only telemetry, dashboards, and knowledge base.
   - `service_account`: Programmatic API access scoped via API keys.

3. **Security Headers Middleware**:
   - `X-Frame-Options: DENY`
   - `X-Content-Type-Options: nosniff`
   - `X-XSS-Protection: 1; mode=block`
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Permissions-Policy: camera=(), microphone=(), geolocation=()`

4. **Human-In-The-Loop (HITL) Approval Gate**:
   - High-risk agent actions (`risk_level: critical` or `high`) trigger an approval request.
   - Execution is paused in the LangGraph state machine until explicitly approved by an operator or admin.

---

## Consequences

### Positive:
- Fully compliant with enterprise SOC 2 security requirements.
- Immutability of security audit trail via append-only `audit_logs` model.
- Prevents accidental automated actions on production systems.

### Negative:
- HITL approval introduces minor latency for high-risk autonomous workflows requiring operator input.
