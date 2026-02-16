"""WebSocket endpoints — live data streaming with JWT authentication.

Two WebSocket channels:
- /ws/v1/ticks    — live market tick stream
- /ws/v1/agent-log — real-time AI agent "thinking" stream
"""

from __future__ import annotations

import asyncio
import json

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.dependencies import get_cache, get_cached_settings
from app.shared.security import decode_token

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
        if ws in self._connections:
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


async def _authenticate_ws(ws: WebSocket, token: str | None) -> dict | None:
    """Validate JWT token for WebSocket connections.

    Returns user payload on success, None on failure.
    """
    if not token:
        await ws.close(code=4001, reason="Missing authentication token")
        return None

    settings = get_cached_settings()
    try:
        payload = decode_token(token, settings.jwt_secret_key, settings.jwt_algorithm)
        return payload
    except Exception:
        await ws.close(code=4003, reason="Invalid authentication token")
        return None


@ws_router.websocket("/ws/v1/ticks")
async def tick_stream(ws: WebSocket, token: str | None = Query(None)) -> None:
    """Stream live market ticks from Redis pub/sub (JWT required)."""
    user = await _authenticate_ws(ws, token)
    if user is None:
        return

    await tick_manager.connect(ws)
    logger.info("ws_tick_connected", user=user.get("sub"), total=tick_manager.count)
    pubsub = None
    try:
        cache = get_cache()
        pubsub = await cache.subscribe("ticks")

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if message and message["type"] == "message":
                await ws.send_text(str(message["data"]))

            # Also check for client messages (ping/subscribe)
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=0.1)
                logger.debug("ws_tick_client_message", data=data)
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        tick_manager.disconnect(ws)
        logger.info("ws_tick_disconnected", total=tick_manager.count)
    except Exception as exc:
        logger.error("ws_tick_error", error=str(exc))
        tick_manager.disconnect(ws)
    finally:
        if pubsub:
            await pubsub.unsubscribe("ticks")
            await pubsub.aclose()


@ws_router.websocket("/ws/v1/agent-log")
async def agent_log_stream(ws: WebSocket, token: str | None = Query(None)) -> None:
    """Stream real-time AI agent analysis logs (JWT required)."""
    user = await _authenticate_ws(ws, token)
    if user is None:
        return

    await agent_log_manager.connect(ws)
    logger.info("ws_agent_connected", user=user.get("sub"), total=agent_log_manager.count)
    pubsub = None
    try:
        cache = get_cache()
        pubsub = await cache.subscribe("agent_logs")

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
    finally:
        if pubsub:
            await pubsub.unsubscribe("agent_logs")
            await pubsub.aclose()
