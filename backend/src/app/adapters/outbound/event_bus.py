"""In-process event bus for domain events.

Provides a simple publish/subscribe mechanism for decoupled communication
between application services.  For production scaling, swap for a message
broker adapter (Redis Streams, Kafka, etc.).
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine

import structlog

from app.domain.events import DomainEvent
from app.ports.outbound import EventBusPort

logger = structlog.get_logger(__name__)

EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]


class InProcessEventBus(EventBusPort):
    """Async in-memory event bus with fan-out to multiple subscribers."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    async def publish(self, event: DomainEvent) -> None:
        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            logger.debug("event_no_handlers", event_type=event.event_type)
            return

        logger.info(
            "event_published",
            event_type=event.event_type,
            handler_count=len(handlers),
        )

        # Fire-and-forget — handlers run concurrently but failures are logged
        results = await asyncio.gather(
            *(h(event) for h in handlers),
            return_exceptions=True,
        )
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "event_handler_error",
                    event_type=event.event_type,
                    handler_index=i,
                    error=str(result),
                )

    def subscribe(self, event_type: str, handler: Any) -> None:
        self._handlers[event_type].append(handler)
        logger.debug("event_handler_registered", event_type=event_type)
