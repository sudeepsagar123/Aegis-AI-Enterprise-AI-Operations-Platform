"""
Unit tests for the Webhook & Event Notification Service.
"""

from __future__ import annotations

import pytest
from app.services.webhooks import (
    WebhookPayload,
    WebhookService,
    WebhookEventType,
    WebhookDestinationType,
    WebhookDeliveryResult,
)


class TestWebhookPayload:
    def test_payload_creation(self):
        payload = WebhookPayload(
            event_type="incident.created",
            org_id="org-123",
            data={"title": "Test Incident", "severity": "critical"},
        )
        assert payload.event_type == "incident.created"
        assert payload.org_id == "org-123"
        assert payload.event_id  # auto-generated

    def test_payload_to_dict(self):
        payload = WebhookPayload(
            event_type="incident.created",
            org_id="org-123",
            data={"title": "Test"},
        )
        d = payload.to_dict()
        assert d["event_type"] == "incident.created"
        assert d["org_id"] == "org-123"
        assert "event_id" in d
        assert "timestamp" in d

    def test_payload_signing(self):
        payload = WebhookPayload(
            event_type="test.event",
            org_id="org-456",
            data={"key": "value"},
        )
        sig1 = payload.sign("my-secret")
        sig2 = payload.sign("my-secret")
        assert sig1 == sig2  # deterministic

        sig3 = payload.sign("different-secret")
        assert sig1 != sig3  # different secrets produce different signatures

    def test_payload_signing_is_hmac_sha256(self):
        payload = WebhookPayload(
            event_type="test.event",
            org_id="org-789",
            data={},
        )
        sig = payload.sign("secret")
        assert len(sig) == 64  # SHA256 hex digest length


class TestWebhookService:
    def test_service_initialization(self):
        service = WebhookService(timeout=5.0, max_retries=2)
        assert service.timeout == 5.0
        assert service.max_retries == 2

    def test_delivery_log_starts_empty(self):
        service = WebhookService()
        assert service.get_delivery_log() == []

    def test_slack_payload_formatting(self):
        service = WebhookService()
        payload = WebhookPayload(
            event_type="incident.created",
            org_id="org-123",
            data={"title": "High CPU", "severity": "critical"},
        )
        formatted = service._format_payload(payload, WebhookDestinationType.SLACK)
        assert "attachments" in formatted
        assert formatted["attachments"][0]["color"] == "#FF0000"  # critical = red

    def test_pagerduty_payload_formatting(self):
        service = WebhookService()
        payload = WebhookPayload(
            event_type="incident.created",
            org_id="org-123",
            data={"title": "DB Connection Pool", "severity": "high"},
            metadata={"routing_key": "test-key"},
        )
        formatted = service._format_payload(payload, WebhookDestinationType.PAGERDUTY)
        assert formatted["event_action"] == "trigger"
        assert formatted["payload"]["severity"] == "error"  # high -> error

    def test_teams_payload_formatting(self):
        service = WebhookService()
        payload = WebhookPayload(
            event_type="incident.resolved",
            org_id="org-123",
            data={"severity": "medium"},
        )
        formatted = service._format_payload(payload, WebhookDestinationType.TEAMS)
        assert formatted["type"] == "message"
        assert "attachments" in formatted

    def test_generic_payload_formatting(self):
        service = WebhookService()
        payload = WebhookPayload(
            event_type="test.event",
            org_id="org-123",
            data={"foo": "bar"},
        )
        formatted = service._format_payload(payload, WebhookDestinationType.GENERIC)
        assert formatted["event_type"] == "test.event"
        assert formatted["data"]["foo"] == "bar"


class TestWebhookEventTypes:
    def test_incident_event_types(self):
        assert WebhookEventType.INCIDENT_CREATED == "incident.created"
        assert WebhookEventType.INCIDENT_RESOLVED == "incident.resolved"
        assert WebhookEventType.INCIDENT_ESCALATED == "incident.escalated"

    def test_agent_event_types(self):
        assert WebhookEventType.AGENT_RUN_STARTED == "agent.run.started"
        assert WebhookEventType.AGENT_RUN_COMPLETED == "agent.run.completed"

    def test_approval_event_types(self):
        assert WebhookEventType.APPROVAL_REQUESTED == "approval.requested"
        assert WebhookEventType.APPROVAL_DECIDED == "approval.decided"


class TestWebhookDeliveryResult:
    def test_successful_delivery(self):
        result = WebhookDeliveryResult(
            success=True, status_code=200, duration_ms=45.2, attempt=1,
        )
        assert result.success is True
        assert result.status_code == 200

    def test_failed_delivery(self):
        result = WebhookDeliveryResult(
            success=False, error="Connection refused", attempt=3,
        )
        assert result.success is False
        assert result.error == "Connection refused"
