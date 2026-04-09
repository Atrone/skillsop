"""Simple in-memory event bus for platform containers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable


class EventBus:
    """Publish/subscribe event bus used across containers."""

    def __init__(self) -> None:
        # Block comment:
        # Subscribers are tracked per event name to emulate topic routing.
        # Line comment: each event name maps to a list of callables.
        self._subscribers: dict[str, list[Callable[[dict[str, Any]], None]]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: Callable[[dict[str, Any]], None]) -> None:
        """Register an event handler for one event name."""
        # Block comment:
        # Duplicate subscription is allowed so that tests can observe repeated handlers.
        # Line comment: append handler to the event subscriber list.
        self._subscribers[event_name].append(handler)

    def publish(self, event_name: str, payload: dict[str, Any]) -> None:
        """Publish one event payload to all subscribers."""
        # Block comment:
        # The bus dispatches synchronously to preserve deterministic test behavior.
        # Line comment: iterate over a shallow copy to avoid mutation during dispatch.
        for handler in list(self._subscribers.get(event_name, [])):
            # Line comment: invoke each handler with the original payload.
            handler(payload)


# Block comment:
# This alias keeps type usage explicit across container modules.
# Line comment: expose a semantic event-bus type name for the platform.
PlatformEventBus = EventBus
