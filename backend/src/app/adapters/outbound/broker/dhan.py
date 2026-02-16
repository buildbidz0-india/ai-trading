"""Dhan broker adapter — production order execution via Dhan API.

Dhan (https://dhan.co) REST API v2 integration for the Indian stock market.
Implements the BrokerPort interface with async httpx calls.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.domain.entities import Order
from app.ports.outbound import BrokerPort

logger = structlog.get_logger(__name__)

_BASE_URL = "https://api.dhan.co/v2"


class DhanBrokerAdapter(BrokerPort):
    """Production broker adapter for Dhan.

    Requires:
        - ``dhan_client_id``  (DHAN_CLIENT_ID)
        - ``dhan_access_token`` (DHAN_ACCESS_TOKEN)
    """

    def __init__(self, client_id: str, access_token: str, *, timeout: float = 30.0) -> None:
        self._client_id = client_id
        self._headers = {
            "Content-Type": "application/json",
            "access-token": access_token,
        }
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers=self._headers,
            timeout=timeout,
        )
        logger.info("dhan_adapter_initialized", client_id=client_id)

    # ── Mappings ──────────────────────────────────────────────
    _EXCHANGE_MAP: dict[str, str] = {
        "NSE": "NSE_EQ",
        "BSE": "BSE_EQ",
        "NFO": "NSE_FNO",
        "BFO": "BSE_FNO",
        "MCX": "MCX_COMM",
    }

    _SIDE_MAP: dict[str, str] = {"BUY": "BUY", "SELL": "SELL"}

    _ORDER_TYPE_MAP: dict[str, str] = {
        "MARKET": "MARKET",
        "LIMIT": "LIMIT",
        "STOP_LOSS": "STOP_LOSS_MARKET",
        "STOP_LOSS_LIMIT": "STOP_LOSS_LIMIT",
    }

    _PRODUCT_TYPE_MAP: dict[str, str] = {
        "CNC": "CNC",
        "MIS": "INTRA",
        "NRML": "MARGIN",
    }

    # ── BrokerPort implementation ─────────────────────────────
    async def place_order(self, order: Order) -> str:
        payload = {
            "transactionType": self._SIDE_MAP.get(order.side.value, order.side.value),
            "exchangeSegment": self._EXCHANGE_MAP.get(order.exchange.value, order.exchange.value),
            "productType": self._PRODUCT_TYPE_MAP.get(
                order.product_type.value, order.product_type.value
            ),
            "orderType": self._ORDER_TYPE_MAP.get(order.order_type.value, order.order_type.value),
            "quantity": order.quantity.value,
            "price": float(order.price.amount),
            "triggerPrice": float(order.trigger_price.amount) if order.trigger_price else 0,
            "validity": "DAY",
            "dhanClientId": self._client_id,
            "correlationId": order.idempotency_key[:20],
        }
        resp = await self._client.post("/orders", json=payload)
        resp.raise_for_status()
        data = resp.json()
        broker_id: str = str(data.get("orderId", data.get("order_id", "")))
        logger.info(
            "dhan_order_placed",
            broker_id=broker_id,
            symbol=str(order.symbol),
            side=order.side.value,
        )
        return broker_id

    async def cancel_order(self, broker_order_id: str) -> bool:
        resp = await self._client.delete(f"/orders/{broker_order_id}")
        if resp.status_code == 200:
            logger.info("dhan_order_cancelled", broker_id=broker_order_id)
            return True
        logger.warning("dhan_cancel_failed", broker_id=broker_order_id, status=resp.status_code)
        return False

    async def get_positions(self) -> list[dict[str, Any]]:
        resp = await self._client.get("/positions")
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def get_order_status(self, broker_order_id: str) -> dict[str, Any]:
        resp = await self._client.get(f"/orders/{broker_order_id}")
        resp.raise_for_status()
        return resp.json()

    async def get_option_chain(self, symbol: str, expiry: str) -> dict[str, Any]:
        resp = await self._client.get(
            "/optionchain",
            params={"symbol": symbol, "expiry": expiry},
        )
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()
