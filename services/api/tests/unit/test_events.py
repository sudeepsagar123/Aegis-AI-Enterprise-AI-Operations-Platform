"""
Unit tests for the Internal Event Bus.
"""

from __future__ import annotations

import pytest
from app.core.events import Event, EventBus


@pytest.mark.asyncio
async def test_event_bus_subscribe_and_publish():
    bus = EventBus()
    received_events = []

    async def sample_handler(event_dict):
        received_events.append(event_dict)

    bus.subscribe("incident.created", sample_handler)

    event = Event(
        event_type="incident.created",
        org_id="org-123",
        data={"title": "High Latency"},
    )

    await bus.publish(event)

    assert len(received_events) == 1
    assert received_events[0]["event_type"] == "incident.created"
    assert received_events[0]["org_id"] == "org-123"


@pytest.mark.asyncio
async def test_event_bus_multiple_subscribers():
    bus = EventBus()
    count = [0]

    async def h1(event_dict):
        count[0] += 1

    async def h2(event_dict):
        count[0] += 10

    bus.subscribe("agent.completed", h1)
    bus.subscribe("agent.completed", h2)

    await bus.publish(Event(event_type="agent.completed", org_id="org-123", data={}))

    assert count[0] == 11


@pytest.mark.asyncio
async def test_event_bus_unsubscribe():
    bus = EventBus()
    calls = []

    async def h(event_dict):
        calls.append(True)

    bus.subscribe("test.event", h)
    bus.unsubscribe("test.event", h)

    await bus.publish(Event(event_type="test.event", org_id="org-123", data={}))

    assert len(calls) == 0


@pytest.mark.asyncio
async def test_event_bus_history():
    bus = EventBus()

    await bus.publish(Event(event_type="e1", org_id="org-1", data={}))
    await bus.publish(Event(event_type="e2", org_id="org-1", data={}))

    history = bus.get_history()
    assert len(history) == 2
    assert history[0].event_type == "e1"
    assert history[1].event_type == "e2"
