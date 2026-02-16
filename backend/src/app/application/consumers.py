"""Event consumers (handlers) for domain events.

Bridges internal EventBus to external systems like Redis Pub/Sub for WebSockets.
"""
import json
import structlog
from datetime import datetime

from app.domain.events import AgentAnalysisCompletedEvent
from app.ports.outbound import CachePort

logger = structlog.get_logger(__name__)

class AgentLogConsumer:
    """Consumes AgentAnalysisCompletedEvent and publishes to Redis 'agent_logs' channel."""

    def __init__(self, cache: CachePort):
        self._cache = cache

    async def handle_analysis_completed(self, event: AgentAnalysisCompletedEvent) -> None:
        """Handle event and broadcast."""
        try:
            message = {
                "type": "agent_log",
                "role": event.agent_role,
                "provider": event.provider,
                "confidence": event.confidence,
                "latency_ms": event.latency_ms,
                "summary": event.summary,
                "timestamp": event.timestamp.isoformat(),
            }
            # Publish to Redis channel (must match ws_router subscription)
            await self._cache.publish("agent_logs", json.dumps(message))
            logger.debug("agent_log_broadcast", role=event.agent_role)
        except Exception as e:
            logger.error("agent_log_broadcast_failed", error=str(e))
