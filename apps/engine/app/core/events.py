import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List
from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_module: str
    payload: Dict[str, Any]


EventHandler = Callable[[EventEnvelope], Coroutine[Any, Any, None]]


class EventBus:
    """
    In-memory asynchronous event bus implementing the publish-subscribe pattern.
    Enables loose coupling between scanner, CRM, scoring, and UI websocket layers.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._history: List[EventEnvelope] = []

    def subscribe(self, event_type: str, handler: EventHandler):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def publish(
        self, event_type: str, source_module: str, payload: Dict[str, Any]
    ) -> EventEnvelope:
        event = EventEnvelope(
            event_type=event_type, source_module=source_module, payload=payload
        )
        self._history.append(event)
        # Cap event history to 1000 items
        if len(self._history) > 1000:
            self._history.pop(0)

        handlers = self._subscribers.get(event_type, [])
        # Also run wildcard handlers if any
        wildcard_handlers = self._subscribers.get("*", [])
        all_handlers = handlers + wildcard_handlers

        for h in all_handlers:
            asyncio.create_task(self._safe_execute(h, event))

        return event

    async def _safe_execute(self, handler: EventHandler, event: EventEnvelope):
        try:
            await handler(event)
        except Exception as e:
            # Avoid crashing the bus on individual subscriber error
            print(f"[EventBus] Error in handler for {event.event_type}: {e}")


event_bus = EventBus()
