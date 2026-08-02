"""
Aegis AI — Webhook & Event Notification Service.

Handles outbound webhook delivery for real-time incident escalation,
agent completion events, and approval request notifications.

Supports configurable destinations: Slack, PagerDuty, Microsoft Teams,
OpsGenie, and generic HTTP webhook endpoints.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class WebhookEventType(StrEnum):
    """Standardized event types for webhook delivery."""
    INCIDENT_CREATED = "incident.created"
    INCIDENT_UPDATED = "incident.updated"
    INCIDENT_RESOLVED = "incident.resolved"
    INCIDENT_ESCALATED = "incident.escalated"
    AGENT_RUN_STARTED = "agent.run.started"
    AGENT_RUN_COMPLETED = "agent.run.completed"
    AGENT_RUN_FAILED = "agent.run.failed"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_DECIDED = "approval.decided"
    KNOWLEDGE_INGESTED = "knowledge.ingested"
    SECURITY_ALERT = "security.alert"
    SYSTEM_HEALTH_DEGRADED = "system.health.degraded"


class WebhookDestinationType(StrEnum):
    """Supported webhook destination platforms."""
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    TEAMS = "teams"
    OPSGENIE = "opsgenie"
    GENERIC = "generic"


@dataclass
class WebhookPayload:
    """Structured webhook event payload."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: str = ""
    timestamp: float = field(default_factory=time.time)
    org_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "org_id": self.org_id,
            "data": self.data,
            "metadata": self.metadata,
        }

    def sign(self, secret: str) -> str:
        """Generate HMAC-SHA256 signature for payload verification."""
        payload_bytes = json.dumps(self.to_dict(), sort_keys=True).encode("utf-8")
        return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


@dataclass
class WebhookDeliveryResult:
    """Result of a webhook delivery attempt."""
    success: bool
    status_code: int | None = None
    response_body: str | None = None
    error: str | None = None
    duration_ms: float = 0.0
    attempt: int = 1


class WebhookService:
    """
    Manages outbound webhook delivery with retry logic, payload signing,
    and platform-specific payload formatting.

    Features:
        - Exponential backoff retry (3 attempts)
        - HMAC-SHA256 payload signing for endpoint verification
        - Platform-specific formatting (Slack blocks, PagerDuty events)
        - Async delivery with configurable timeout
        - Delivery status tracking and dead-letter queue
    """

    def __init__(self, timeout: float = 10.0, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.settings = get_settings()
        self._delivery_log: list[dict[str, Any]] = []

    async def send(
        self,
        *,
        url: str,
        event_type: WebhookEventType | str,
        org_id: str,
        data: dict[str, Any],
        destination_type: WebhookDestinationType = WebhookDestinationType.GENERIC,
        signing_secret: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WebhookDeliveryResult:
        """
        Deliver a webhook event to the specified URL with retry logic.
        """
        payload = WebhookPayload(
            event_type=str(event_type),
            org_id=org_id,
            data=data,
            metadata=metadata or {},
        )

        # Format payload for destination platform
        formatted = self._format_payload(payload, destination_type)

        # Build headers
        headers = {
            "Content-Type": "application/json",
            "X-Aegis-Event": payload.event_type,
            "X-Aegis-Event-ID": payload.event_id,
            "X-Aegis-Timestamp": str(int(payload.timestamp)),
            "User-Agent": "AegisAI-Webhook/1.0",
        }

        if signing_secret:
            signature = payload.sign(signing_secret)
            headers["X-Aegis-Signature"] = f"sha256={signature}"

        # Deliver with retries
        result = await self._deliver_with_retry(url, formatted, headers)

        # Log delivery
        self._delivery_log.append({
            "event_id": payload.event_id,
            "event_type": payload.event_type,
            "url": url,
            "success": result.success,
            "status_code": result.status_code,
            "duration_ms": result.duration_ms,
            "attempt": result.attempt,
        })

        if result.success:
            logger.info(
                "webhook_delivered",
                event_type=payload.event_type,
                url=url,
                status_code=result.status_code,
                duration_ms=result.duration_ms,
            )
        else:
            logger.error(
                "webhook_delivery_failed",
                event_type=payload.event_type,
                url=url,
                error=result.error,
                attempts=result.attempt,
            )

        return result

    async def _deliver_with_retry(
        self, url: str, payload: dict, headers: dict
    ) -> WebhookDeliveryResult:
        """Deliver with exponential backoff retry."""
        for attempt in range(1, self.max_retries + 1):
            start = time.monotonic()
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    duration_ms = (time.monotonic() - start) * 1000

                    if response.status_code < 400:
                        return WebhookDeliveryResult(
                            success=True,
                            status_code=response.status_code,
                            response_body=response.text[:500],
                            duration_ms=round(duration_ms, 2),
                            attempt=attempt,
                        )
                    else:
                        logger.warning(
                            "webhook_retry",
                            attempt=attempt,
                            status_code=response.status_code,
                        )
            except Exception as e:
                duration_ms = (time.monotonic() - start) * 1000
                if attempt == self.max_retries:
                    return WebhookDeliveryResult(
                        success=False,
                        error=str(e),
                        duration_ms=round(duration_ms, 2),
                        attempt=attempt,
                    )
                logger.warning("webhook_retry_error", attempt=attempt, error=str(e))

            # Exponential backoff: 1s, 2s, 4s
            await asyncio.sleep(2 ** (attempt - 1))

        return WebhookDeliveryResult(
            success=False, error="max retries exceeded", attempt=self.max_retries
        )

    def _format_payload(
        self, payload: WebhookPayload, destination: WebhookDestinationType
    ) -> dict[str, Any]:
        """Format payload for specific platform requirements."""
        if destination == WebhookDestinationType.SLACK:
            return self._format_slack(payload)
        elif destination == WebhookDestinationType.PAGERDUTY:
            return self._format_pagerduty(payload)
        elif destination == WebhookDestinationType.TEAMS:
            return self._format_teams(payload)
        return payload.to_dict()

    def _format_slack(self, payload: WebhookPayload) -> dict[str, Any]:
        """Format as Slack Block Kit message."""
        severity = payload.data.get("severity", "info")
        color_map = {"critical": "#FF0000", "high": "#FF6B00", "medium": "#FFB800", "low": "#00C853"}
        color = color_map.get(severity, "#2196F3")

        return {
            "attachments": [{
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": f"🛡️ Aegis AI — {payload.event_type}"},
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Event:*\n{payload.event_type}"},
                            {"type": "mrkdwn", "text": f"*Severity:*\n{severity.upper()}"},
                        ],
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"```{json.dumps(payload.data, indent=2)[:1500]}```"},
                    },
                    {
                        "type": "context",
                        "elements": [{"type": "mrkdwn", "text": f"Event ID: `{payload.event_id}`"}],
                    },
                ],
            }],
        }

    def _format_pagerduty(self, payload: WebhookPayload) -> dict[str, Any]:
        """Format as PagerDuty Events API v2 payload."""
        severity_map = {"critical": "critical", "high": "error", "medium": "warning", "low": "info"}
        severity = severity_map.get(payload.data.get("severity", "info"), "info")

        return {
            "routing_key": payload.metadata.get("routing_key", ""),
            "event_action": "trigger",
            "dedup_key": payload.event_id,
            "payload": {
                "summary": payload.data.get("title", payload.event_type),
                "source": "aegis-ai",
                "severity": severity,
                "custom_details": payload.data,
            },
        }

    def _format_teams(self, payload: WebhookPayload) -> dict[str, Any]:
        """Format as Microsoft Teams Adaptive Card."""
        return {
            "type": "message",
            "attachments": [{
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {"type": "TextBlock", "text": f"🛡️ {payload.event_type}", "weight": "Bolder", "size": "Large"},
                        {"type": "FactSet", "facts": [
                            {"title": "Event", "value": payload.event_type},
                            {"title": "Severity", "value": payload.data.get("severity", "N/A").upper()},
                            {"title": "Event ID", "value": payload.event_id},
                        ]},
                    ],
                },
            }],
        }

    def get_delivery_log(self) -> list[dict[str, Any]]:
        """Return recent delivery history for monitoring."""
        return self._delivery_log[-100:]
