"""
Aegis AI — Internal Event Bus.

Provides an in-memory asynchronous pub/sub event bus for decoupled
domain event handling (e.g. IncidentCreated -> WebhookDelivery, AuditLog, PrometheusMetrics).
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine
import uuid
import time

from app.core.logging import get_logger

logger = get_logger(__name__)

EventHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


@dataclass
class Event:
    """Domain event container."""
    event_type: str
    org_id: str
    data: dict[str, Any]
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timestamp: float = field(default_factory=time.time)


class EventBus:
    """
    In-memory asynchronous pub/sub event bus.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[Event] = []

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe a handler function to a specific event type."""
        self._subscribers[event_type].append(handler)
        logger.debug("event_subscribed", event_type=event_type, handler=handler.__name__)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe a handler function."""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers asynchronously.
        """
        self._history.append(event)
        handlers = self._subscribers.get(event.event_type, [])

        if not handlers:
            logger.debug("event_published_no_subscribers", event_type=event.event_type)
            return

        logger.info(
            "event_published",
            event_type=event.event_type,
            subscriber_count=len(handlers),
            event_id=event.event_id,
        )

        tasks = [self._safely_execute(h, event) for h in handlers]
        await asyncio.gather(*tasks)

    async def _safely_execute(self, handler: EventHandler, event: Event) -> None:
        """Execute a handler safely catching any exceptions."""
        try:
            await handler(event.__dict__)
        except Exception as e:
            logger.error(
                "event_handler_failed",
                event_type=event.event_type,
                handler=handler.__name__,
                error=str(e),
            )

    def get_history(self, limit: int = 50) -> list[Event]:
        """Get recent event history."""
        return self._history[-limit:]


# Global event bus singleton instance
event_bus = EventBus()
