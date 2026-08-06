"""
Aegis AI — Database Seed Script.

Populates the database with demo data for development and testing.
Run with: poetry run python -m app.db.seed
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger, setup_logging
from app.core.security import hash_password
from app.db.session import async_session_factory, engine, Base
from app.db import models  # noqa: F401 — ensure all models are registered
from app.domain.enums import IncidentSeverity, IncidentStatus, IncidentSource, Role

logger = get_logger(__name__)


async def seed_database() -> None:
    """Create demo organization, users, and sample incidents."""
    setup_logging()

    # Create tables if they don't exist
    async with engine.begin() as conn:
        if conn.dialect.name == "postgresql":
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        # Check if already seeded
        result = await session.execute(
            text("SELECT COUNT(*) FROM organizations")
        )
        count = result.scalar()
        if count and count > 0:
            logger.info("database_already_seeded", org_count=count)
            return

        # ── Organization ─────────────────────────────────────────────────
        # Deterministic IDs so dev JWT tokens can reference them reliably
        org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        org = models.Organization(
            id=org_id,
            name="Acme Corp",
            slug="acme-corp",
            plan="enterprise",
            settings={"theme": "dark", "timezone": "America/New_York"},
        )
        session.add(org)

        # ── Users ────────────────────────────────────────────────────────
        admin_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
        admin = models.User(
            id=admin_id,
            org_id=org_id,
            email="admin@acme.com",
            hashed_password=hash_password("Admin@123!"),
            full_name="Sarah Chen",
            role=Role.ORG_ADMIN.value,
            is_active=True,
        )
        session.add(admin)

        operator_id = uuid.uuid4()
        operator = models.User(
            id=operator_id,
            org_id=org_id,
            email="operator@acme.com",
            hashed_password=hash_password("Operator@123!"),
            full_name="Marcus Johnson",
            role=Role.OPERATOR.value,
            is_active=True,
        )
        session.add(operator)

        viewer_id = uuid.uuid4()
        viewer = models.User(
            id=viewer_id,
            org_id=org_id,
            email="viewer@acme.com",
            hashed_password=hash_password("Viewer@123!"),
            full_name="Emily Rodriguez",
            role=Role.VIEWER.value,
            is_active=True,
        )
        session.add(viewer)

        # ── Sample Incidents ─────────────────────────────────────────────
        incidents_data = [
            {
                "title": "Production API latency spike — p99 > 2s",
                "description": "Grafana alert: API response times exceeded SLO threshold. Affecting checkout flow.",
                "severity": IncidentSeverity.CRITICAL.value,
                "status": IncidentStatus.INVESTIGATING.value,
                "source": IncidentSource.GRAFANA.value,
                "reported_by": admin_id,
                "assigned_to": operator_id,
                "tags": ["api", "latency", "production"],
                "affected_services": ["api-gateway", "checkout-service", "payment-service"],
                "acknowledged_at": datetime.now(UTC) - timedelta(minutes=15),
            },
            {
                "title": "Memory leak in worker pods — OOMKilled 3x in 1h",
                "description": "Kubernetes worker pods being OOMKilled. Memory usage growing linearly.",
                "severity": IncidentSeverity.HIGH.value,
                "status": IncidentStatus.OPEN.value,
                "source": IncidentSource.PROMETHEUS.value,
                "reported_by": None,
                "tags": ["kubernetes", "memory", "worker"],
                "affected_services": ["worker-service"],
            },
            {
                "title": "Database connection pool exhaustion during peak",
                "description": "PostgreSQL connection pool saturated. New connections being rejected.",
                "severity": IncidentSeverity.HIGH.value,
                "status": IncidentStatus.IDENTIFIED.value,
                "source": IncidentSource.DATADOG.value,
                "reported_by": operator_id,
                "assigned_to": admin_id,
                "tags": ["database", "connection-pool", "capacity"],
                "affected_services": ["postgres-primary"],
                "root_cause": "Slow queries from analytics dashboard holding connections.",
            },
            {
                "title": "SSL certificate expiring in 7 days",
                "description": "TLS certificate for api.acme.com expires on 2024-02-15.",
                "severity": IncidentSeverity.MEDIUM.value,
                "status": IncidentStatus.MONITORING.value,
                "source": IncidentSource.AGENT.value,
                "reported_by": None,
                "tags": ["ssl", "certificate", "security"],
                "affected_services": ["nginx-ingress"],
            },
            {
                "title": "Elevated 5xx error rate on /api/v1/search",
                "description": "5xx rate increased from 0.1% to 2.3% in the last 30 minutes.",
                "severity": IncidentSeverity.MEDIUM.value,
                "status": IncidentStatus.RESOLVED.value,
                "source": IncidentSource.PROMETHEUS.value,
                "reported_by": admin_id,
                "assigned_to": operator_id,
                "tags": ["api", "errors", "search"],
                "affected_services": ["search-service", "elasticsearch"],
                "root_cause": "Elasticsearch cluster yellow status due to unassigned shards.",
                "resolution": "Reassigned shards and increased replica count.",
                "resolved_at": datetime.now(UTC) - timedelta(hours=2),
            },
        ]

        for inc_data in incidents_data:
            incident = models.Incident(org_id=org_id, **inc_data)
            session.add(incident)

        await session.commit()
        logger.info(
            "database_seeded",
            org="Acme Corp",
            users=3,
            incidents=len(incidents_data),
        )
        print("\n[OK] Database seeded successfully!")
        print("   Organization: Acme Corp")
        print("   Admin:    admin@acme.com / Admin@123!")
        print("   Operator: operator@acme.com / Operator@123!")
        print("   Viewer:   viewer@acme.com / Viewer@123!")
        print(f"   Incidents: {len(incidents_data)} sample incidents created")


if __name__ == "__main__":
    asyncio.run(seed_database())
