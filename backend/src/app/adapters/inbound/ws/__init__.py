"""WebSocket endpoints — live data streaming.

Two WebSocket channels:
- /ws/v1/ticks    — live market tick stream
- /ws/v1/agent-log — real-time AI agent "thinking" stream
"""

from __future__ import annotations

import asyncio
import json

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.dependencies import get_cache

logger = structlog.get_logger(__name__)

ws_router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manages WebSocket connections for a channel."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.remove(ws)

    async def broadcast(self, message: str) -> None:
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.remove(ws)

    @property
    def count(self) -> int:
        return len(self._connections)


tick_manager = ConnectionManager()
agent_log_manager = ConnectionManager()


@ws_router.websocket("/ws/v1/ticks")
async def tick_stream(ws: WebSocket) -> None:
    """Stream live market ticks from Redis pub/sub."""
    await tick_manager.connect(ws)
    logger.info("ws_tick_connected", total=tick_manager.count)
    try:
        cache = get_cache()
        # Subscribe to Redis tick channel
        pubsub = cache._client.pubsub()
        await pubsub.subscribe("ticks")

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if message and message["type"] == "message":
                await ws.send_text(str(message["data"]))

            # Also check for client messages (ping/subscribe)
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=0.1)
                # Client can send subscribe/unsubscribe commands
                logger.debug("ws_tick_client_message", data=data)
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        tick_manager.disconnect(ws)
        logger.info("ws_tick_disconnected", total=tick_manager.count)
    except Exception as exc:
        logger.error("ws_tick_error", error=str(exc))
        tick_manager.disconnect(ws)


@ws_router.websocket("/ws/v1/agent-log")
async def agent_log_stream(ws: WebSocket) -> None:
    """Stream real-time AI agent analysis logs."""
    await agent_log_manager.connect(ws)
    logger.info("ws_agent_connected", total=agent_log_manager.count)
    try:
        cache = get_cache()
        pubsub = cache._client.pubsub()
        await pubsub.subscribe("agent_logs")

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if message and message["type"] == "message":
                await ws.send_text(str(message["data"]))

            try:
                await asyncio.wait_for(ws.receive_text(), timeout=0.1)
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        agent_log_manager.disconnect(ws)
        logger.info("ws_agent_disconnected", total=agent_log_manager.count)
    except Exception as exc:
        logger.error("ws_agent_error", error=str(exc))
        agent_log_manager.disconnect(ws)
