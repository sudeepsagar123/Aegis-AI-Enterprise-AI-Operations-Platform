"""
Aegis AI — Domain Enumerations.

Canonical enums used across all layers. Defined in the domain layer
because they represent core business concepts (incident severity,
agent types, etc.) that must remain framework-agnostic.
"""

from __future__ import annotations

from enum import StrEnum


# ── User & RBAC ──────────────────────────────────────────────────────────────


class Role(StrEnum):
    """System roles with hierarchical permissions."""
    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "org_admin"
    TEAM_LEAD = "team_lead"
    OPERATOR = "operator"
    VIEWER = "viewer"
    SERVICE_ACCOUNT = "service_account"


class Permission(StrEnum):
    """Granular permissions for RBAC enforcement."""
    # Conversations
    CONVERSATION_CREATE = "conversation:create"
    CONVERSATION_READ = "conversation:read"
    CONVERSATION_DELETE = "conversation:delete"

    # Agents
    AGENT_EXECUTE = "agent:execute"
    AGENT_CONFIGURE = "agent:configure"
    AGENT_APPROVE = "agent:approve"

    # Integrations
    INTEGRATION_READ = "integration:read"
    INTEGRATION_CONFIGURE = "integration:configure"
    INTEGRATION_EXECUTE = "integration:execute"

    # Knowledge
    KNOWLEDGE_READ = "knowledge:read"
    KNOWLEDGE_WRITE = "knowledge:write"
    KNOWLEDGE_DELETE = "knowledge:delete"

    # Incidents
    INCIDENT_CREATE = "incident:create"
    INCIDENT_READ = "incident:read"
    INCIDENT_UPDATE = "incident:update"
    INCIDENT_ASSIGN = "incident:assign"

    # Administration
    ADMIN_USERS = "admin:users"
    ADMIN_SETTINGS = "admin:settings"
    ADMIN_AUDIT = "admin:audit"

    # Workflows
    WORKFLOW_CREATE = "workflow:create"
    WORKFLOW_EXECUTE = "workflow:execute"
    WORKFLOW_APPROVE = "workflow:approve"


# Role → Permission mapping
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.SUPER_ADMIN: set(Permission),  # All permissions
    Role.ORG_ADMIN: {
        Permission.CONVERSATION_CREATE, Permission.CONVERSATION_READ,
        Permission.CONVERSATION_DELETE, Permission.AGENT_EXECUTE,
        Permission.AGENT_CONFIGURE, Permission.AGENT_APPROVE,
        Permission.INTEGRATION_READ, Permission.INTEGRATION_CONFIGURE,
        Permission.INTEGRATION_EXECUTE, Permission.KNOWLEDGE_READ,
        Permission.KNOWLEDGE_WRITE, Permission.KNOWLEDGE_DELETE,
        Permission.INCIDENT_CREATE, Permission.INCIDENT_READ,
        Permission.INCIDENT_UPDATE, Permission.INCIDENT_ASSIGN,
        Permission.ADMIN_USERS, Permission.ADMIN_SETTINGS,
        Permission.ADMIN_AUDIT, Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_EXECUTE, Permission.WORKFLOW_APPROVE,
    },
    Role.TEAM_LEAD: {
        Permission.CONVERSATION_CREATE, Permission.CONVERSATION_READ,
        Permission.AGENT_EXECUTE, Permission.AGENT_APPROVE,
        Permission.INTEGRATION_READ, Permission.INTEGRATION_EXECUTE,
        Permission.KNOWLEDGE_READ, Permission.KNOWLEDGE_WRITE,
        Permission.INCIDENT_CREATE, Permission.INCIDENT_READ,
        Permission.INCIDENT_UPDATE, Permission.INCIDENT_ASSIGN,
        Permission.WORKFLOW_CREATE, Permission.WORKFLOW_EXECUTE,
        Permission.WORKFLOW_APPROVE,
    },
    Role.OPERATOR: {
        Permission.CONVERSATION_CREATE, Permission.CONVERSATION_READ,
        Permission.AGENT_EXECUTE, Permission.INTEGRATION_READ,
        Permission.INTEGRATION_EXECUTE, Permission.KNOWLEDGE_READ,
        Permission.INCIDENT_CREATE, Permission.INCIDENT_READ,
        Permission.INCIDENT_UPDATE, Permission.WORKFLOW_EXECUTE,
    },
    Role.VIEWER: {
        Permission.CONVERSATION_READ, Permission.INTEGRATION_READ,
        Permission.KNOWLEDGE_READ, Permission.INCIDENT_READ,
    },
    Role.SERVICE_ACCOUNT: {
        Permission.AGENT_EXECUTE, Permission.INTEGRATION_EXECUTE,
        Permission.KNOWLEDGE_READ, Permission.INCIDENT_CREATE,
        Permission.INCIDENT_READ, Permission.WORKFLOW_EXECUTE,
    },
}


# ── Incident ─────────────────────────────────────────────────────────────────


class IncidentSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IncidentStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentSource(StrEnum):
    MANUAL = "manual"
    PROMETHEUS = "prometheus"
    GRAFANA = "grafana"
    DATADOG = "datadog"
    PAGERDUTY = "pagerduty"
    SLACK = "slack"
    WEBHOOK = "webhook"
    AGENT = "agent"


# ── Agent ────────────────────────────────────────────────────────────────────


class AgentType(StrEnum):
    COORDINATOR = "coordinator"
    INCIDENT = "incident"
    MONITORING = "monitoring"
    INVESTIGATION = "investigation"
    LOG_ANALYSIS = "log_analysis"
    ROOT_CAUSE = "root_cause"
    DEPLOYMENT = "deployment"
    KNOWLEDGE = "knowledge"
    SECURITY = "security"
    PLANNING = "planning"
    REPORT = "report"


class AgentRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ── Document & RAG ───────────────────────────────────────────────────────────


class DocumentSourceType(StrEnum):
    UPLOAD = "upload"
    WEB_CRAWL = "web_crawl"
    CONFLUENCE = "confluence"
    GITHUB = "github"
    SLACK = "slack"
    JIRA = "jira"
    API = "api"


class ProcessingStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Approval ─────────────────────────────────────────────────────────────────


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── Audit ────────────────────────────────────────────────────────────────────


class AuditAction(StrEnum):
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_REGISTER = "user.register"
    USER_UPDATE = "user.update"
    INCIDENT_CREATE = "incident.create"
    INCIDENT_UPDATE = "incident.update"
    INCIDENT_ASSIGN = "incident.assign"
    INCIDENT_RESOLVE = "incident.resolve"
    AGENT_RUN_START = "agent.run.start"
    AGENT_RUN_COMPLETE = "agent.run.complete"
    APPROVAL_DECIDE = "approval.decide"
    DOCUMENT_UPLOAD = "document.upload"
    KNOWLEDGE_SEARCH = "knowledge.search"
    WORKFLOW_EXECUTE = "workflow.execute"
    SETTINGS_UPDATE = "settings.update"
    API_KEY_CREATE = "api_key.create"
    API_KEY_REVOKE = "api_key.revoke"
