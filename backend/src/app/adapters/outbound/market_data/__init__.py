"""Live market data adapters.

Provides WebSocket-based and polling-based market data adapters that
implement the ``MarketDataPort`` interface.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import structlog

from app.ports.outbound import MarketDataPort

logger = structlog.get_logger(__name__)


class WebSocketMarketDataAdapter(MarketDataPort):
    """WebSocket-based live market data adapter.

    Connects to the broker's WebSocket feed and streams ticks.
    Supports automatic reconnection on disconnect.
    """

    def __init__(
        self,
        ws_url: str,
        auth_token: str = "",
        *,
        on_tick: Any = None,
        reconnect_delay: float = 5.0,
        max_reconnect_attempts: int = 10,
    ) -> None:
        self._ws_url = ws_url
        self._auth_token = auth_token
        self._on_tick = on_tick
        self._reconnect_delay = reconnect_delay
        self._max_reconnect_attempts = max_reconnect_attempts
        self._subscribed_symbols: set[str] = set()
        self._ws: Any = None
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def connect(self) -> None:
        """Establish the WebSocket connection and start listening."""
        self._running = True
        self._task = asyncio.create_task(self._connection_loop())
        logger.info("market_data_ws_connecting", url=self._ws_url)

    async def _connection_loop(self) -> None:
        """Reconnection loop with exponential backoff."""
        attempt = 0
        try:
            import websockets  # type: ignore[import-untyped]
        except ImportError:
            logger.error("websockets_not_installed")
            return

        while self._running and attempt < self._max_reconnect_attempts:
            try:
                async with websockets.connect(self._ws_url) as ws:
                    self._ws = ws
                    attempt = 0
                    logger.info("market_data_ws_connected")

                    # Authenticate
                    if self._auth_token:
                        await ws.send(json.dumps({
                            "type": "auth",
                            "token": self._auth_token,
                        }))

                    # Re-subscribe to symbols
                    if self._subscribed_symbols:
                        await ws.send(json.dumps({
                            "type": "subscribe",
                            "symbols": list(self._subscribed_symbols),
                        }))

                    # Listen for ticks
                    async for message in ws:
                        try:
                            tick = json.loads(message) if isinstance(message, str) else message
                            if self._on_tick:
                                await self._on_tick(tick)
                        except Exception as e:
                            logger.warning("tick_parse_error", error=str(e))

            except Exception as e:
                attempt += 1
                wait = min(self._reconnect_delay * (2 ** (attempt - 1)), 60.0)
                logger.warning(
                    "market_data_ws_disconnected",
                    error=str(e),
                    attempt=attempt,
                    retry_in=wait,
                )
                await asyncio.sleep(wait)

        if self._running:
            logger.error("market_data_ws_max_reconnects_exhausted")

    async def disconnect(self) -> None:
        """Close the WebSocket connection."""
        self._running = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("market_data_ws_disconnected_clean")

    async def subscribe(self, symbols: list[str]) -> None:
        """Subscribe to tick data for the given symbols."""
        self._subscribed_symbols.update(symbols)
        if self._ws:
            try:
                await self._ws.send(json.dumps({
                    "type": "subscribe",
                    "symbols": symbols,
                }))
                logger.info("market_data_subscribed", symbols=symbols)
            except Exception as e:
                logger.warning("subscribe_error", error=str(e))

    async def unsubscribe(self, symbols: list[str]) -> None:
        """Unsubscribe from tick data for the given symbols."""
        self._subscribed_symbols -= set(symbols)
        if self._ws:
            try:
                await self._ws.send(json.dumps({
                    "type": "unsubscribe",
                    "symbols": symbols,
                }))
                logger.info("market_data_unsubscribed", symbols=symbols)
            except Exception as e:
                logger.warning("unsubscribe_error", error=str(e))


class PollingMarketDataAdapter(MarketDataPort):
    """REST polling fallback adapter for market data.

    Polls a REST endpoint at a fixed interval when WebSocket is unavailable.
    """

    def __init__(
        self,
        base_url: str,
        auth_headers: dict[str, str] | None = None,
        *,
        on_tick: Any = None,
        poll_interval: float = 2.0,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url
        self._auth_headers = auth_headers or {}
        self._on_tick = on_tick
        self._poll_interval = poll_interval
        self._subscribed_symbols: set[str] = set()
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=auth_headers or {},
            timeout=timeout,
        )
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def connect(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("market_data_polling_started", url=self._base_url)

    async def _poll_loop(self) -> None:
        while self._running:
            if self._subscribed_symbols:
                try:
                    resp = await self._client.get(
                        "/quotes",
                        params={"symbols": ",".join(self._subscribed_symbols)},
                    )
                    resp.raise_for_status()
                    ticks = resp.json()
                    if self._on_tick and isinstance(ticks, list):
                        for tick in ticks:
                            await self._on_tick(tick)
                except Exception as e:
                    logger.warning("polling_error", error=str(e))
            await asyncio.sleep(self._poll_interval)

    async def disconnect(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self._client.aclose()
        logger.info("market_data_polling_stopped")

    async def subscribe(self, symbols: list[str]) -> None:
        self._subscribed_symbols.update(symbols)
        logger.info("polling_subscribed", symbols=symbols)

    async def unsubscribe(self, symbols: list[str]) -> None:
        self._subscribed_symbols -= set(symbols)
        logger.info("polling_unsubscribed", symbols=symbols)


__all__ = [
    "WebSocketMarketDataAdapter",
    "PollingMarketDataAdapter",
]
