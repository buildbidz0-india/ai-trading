"""Zerodha Kite Connect broker adapter.

Zerodha (https://zerodha.com) Kite Connect API v3 integration.
Implements the BrokerPort interface with async httpx calls.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from app.domain.entities import Order
from app.ports.outbound import BrokerPort

logger = structlog.get_logger(__name__)

_BASE_URL = "https://api.kite.trade"


# Shared retry policy for broker interactions
_broker_retry = retry(
    stop=stop_after_attempt(3),  # Max 3 attempts
    wait=wait_exponential(multiplier=1, min=1, max=10),  # Exp backoff 1s -> 10s
    retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException, httpx.HTTPStatusError)),
    before_sleep=before_sleep_log(logger, "WARNING"),
    reraise=True,
)


class ZerodhaBrokerAdapter(BrokerPort):
    """Production broker adapter for Zerodha Kite Connect v3.

    Requires:
        - ``zerodha_api_key``    (ZERODHA_API_KEY)
        - ``zerodha_api_secret`` (ZERODHA_API_SECRET)
        - ``zerodha_access_token`` generated via login flow
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        access_token: str = "",
        *,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._access_token = access_token
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers=self._build_headers(),
            timeout=timeout,
        )
        logger.info("zerodha_adapter_initialized")

    def _build_headers(self) -> dict[str, str]:
        return {
            "X-Kite-Version": "3",
            "Authorization": f"token {self._api_key}:{self._access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def set_access_token(self, token: str) -> None:
        """Called after the OAuth login flow completes."""
        self._access_token = token
        self._client.headers.update(self._build_headers())

    # ── Kite exchange segment mapping ─────────────────────────
    _EXCHANGE_MAP: dict[str, str] = {
        "NSE": "NSE",
        "BSE": "BSE",
        "NFO": "NFO",
        "BFO": "BFO",
        "MCX": "MCX",
    }

    _ORDER_TYPE_MAP: dict[str, str] = {
        "MARKET": "MARKET",
        "LIMIT": "LIMIT",
        "STOP_LOSS": "SL-M",
        "STOP_LOSS_LIMIT": "SL",
    }

    _PRODUCT_MAP: dict[str, str] = {
        "CNC": "CNC",
        "MIS": "MIS",
        "NRML": "NRML",
    }

    # ── BrokerPort implementation ─────────────────────────────
    @_broker_retry
    async def place_order(self, order: Order) -> str:
        params = {
            "tradingsymbol": str(order.symbol),
            "exchange": self._EXCHANGE_MAP.get(order.exchange.value, order.exchange.value),
            "transaction_type": order.side.value,
            "order_type": self._ORDER_TYPE_MAP.get(order.order_type.value, order.order_type.value),
            "product": self._PRODUCT_MAP.get(order.product_type.value, order.product_type.value),
            "quantity": str(order.quantity.value),
            "price": str(float(order.price.amount)),
            "trigger_price": str(float(order.trigger_price.amount)) if order.trigger_price else "0",
            "validity": "DAY",
            "tag": order.idempotency_key[:20],
        }
        resp = await self._client.post("/orders/regular", data=params)
        resp.raise_for_status()
        data = resp.json()
        broker_id: str = str(data.get("data", {}).get("order_id", ""))
        logger.info(
            "zerodha_order_placed",
            broker_id=broker_id,
            symbol=str(order.symbol),
            side=order.side.value,
        )
        return broker_id

    @_broker_retry
    async def cancel_order(self, broker_order_id: str) -> bool:
        try:
            resp = await self._client.delete(f"/orders/regular/{broker_order_id}")
            if resp.status_code == 200:
                logger.info("zerodha_order_cancelled", broker_id=broker_order_id)
                return True
            
            # Handle 404 cleanly
            if resp.status_code == 404:
                return False
                
            resp.raise_for_status()
            logger.warning(
                "zerodha_cancel_failed", broker_id=broker_order_id, status=resp.status_code
            )
            return False
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise e

    @_broker_retry
    async def get_positions(self) -> list[dict[str, Any]]:
        resp = await self._client.get("/portfolio/positions")
        resp.raise_for_status()
        data = resp.json()
        net = data.get("data", {}).get("net", [])
        return net  # type: ignore[no-any-return]

    @_broker_retry
    async def get_order_status(self, broker_order_id: str) -> dict[str, Any]:
        resp = await self._client.get(f"/orders/{broker_order_id}")
        resp.raise_for_status()
        return resp.json().get("data", {})

    @_broker_retry
    async def get_option_chain(self, symbol: str, expiry: str) -> dict[str, Any]:
        # Kite doesn't have a native option chain endpoint — fetch instruments
        resp = await self._client.get("/instruments/NFO")
        resp.raise_for_status()
        return {"symbol": symbol, "expiry": expiry, "raw": "csv_data"}

    async def close(self) -> None:
        await self._client.aclose()
