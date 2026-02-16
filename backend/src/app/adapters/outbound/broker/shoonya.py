"""Shoonya (Finvasia) broker adapter.

Shoonya / Finvasia REST API integration for the Indian stock market.
Implements the BrokerPort interface with async httpx calls.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
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

_BASE_URL = "https://api.shoonya.com/NorenWClientTP"


# Shared retry policy for broker interactions
_broker_retry = retry(
    stop=stop_after_attempt(3),  # Max 3 attempts
    wait=wait_exponential(multiplier=1, min=1, max=10),  # Exp backoff 1s -> 10s
    retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException, httpx.HTTPStatusError)),
    before_sleep=before_sleep_log(logger, "WARNING"),
    reraise=True,
)


class ShoonyaBrokerAdapter(BrokerPort):
    """Production broker adapter for Shoonya (Finvasia).

    Requires:
        - ``shoonya_user_id``   (SHOONYA_USER_ID)
        - ``shoonya_password``  (SHOONYA_PASSWORD)
        - ``shoonya_api_key``   (SHOONYA_API_KEY)
    """

    def __init__(
        self,
        user_id: str,
        password: str,
        api_key: str,
        *,
        timeout: float = 30.0,
    ) -> None:
        self._user_id = user_id
        self._password = password
        self._api_key = api_key
        self._session_token: str = ""
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=timeout,
        )
        logger.info("shoonya_adapter_initialized", user_id=user_id)

    @_broker_retry
    async def login(self) -> str:
        """Authenticate with Shoonya API and store session token."""
        pwd_hash = hashlib.sha256(self._password.encode()).hexdigest()
        app_key = hashlib.sha256(
            f"{self._user_id}|{self._api_key}".encode()
        ).hexdigest()
        payload = {
            "source": "API",
            "apkversion": "1.0.0",
            "uid": self._user_id,
            "pwd": pwd_hash,
            "appkey": app_key,
        }
        resp = await self._client.post("/QuickAuth", json=payload)
        resp.raise_for_status()
        data = resp.json()
        self._session_token = data.get("susertoken", "")
        logger.info("shoonya_login_success", user_id=self._user_id)
        return self._session_token

    def _auth_payload(self) -> dict[str, str]:
        return {"uid": self._user_id, "stoken": self._session_token}

    # ── Exchange mapping ──────────────────────────────────────
    _EXCHANGE_MAP: dict[str, str] = {
        "NSE": "NSE",
        "BSE": "BSE",
        "NFO": "NFO",
        "BFO": "BFO",
        "MCX": "MCX",
    }

    _SIDE_MAP: dict[str, str] = {"BUY": "B", "SELL": "S"}

    _ORDER_TYPE_MAP: dict[str, str] = {
        "MARKET": "MKT",
        "LIMIT": "LMT",
        "STOP_LOSS": "SL-MKT",
        "STOP_LOSS_LIMIT": "SL-LMT",
    }

    _PRODUCT_MAP: dict[str, str] = {
        "CNC": "C",
        "MIS": "I",
        "NRML": "M",
    }

    # ── BrokerPort implementation ─────────────────────────────
    @_broker_retry
    async def place_order(self, order: Order) -> str:
        payload = {
            **self._auth_payload(),
            "exch": self._EXCHANGE_MAP.get(order.exchange.value, order.exchange.value),
            "tsym": str(order.symbol),
            "trantype": self._SIDE_MAP.get(order.side.value, order.side.value),
            "prctyp": self._ORDER_TYPE_MAP.get(order.order_type.value, order.order_type.value),
            "prd": self._PRODUCT_MAP.get(order.product_type.value, order.product_type.value),
            "qty": str(order.quantity.value),
            "prc": str(float(order.price.amount)),
            "ret": "DAY",
        }
        if order.trigger_price:
            payload["trgprc"] = str(float(order.trigger_price.amount))

        resp = await self._client.post("/PlaceOrder", json=payload)
        resp.raise_for_status()
        data = resp.json()
        broker_id: str = str(data.get("norenordno", ""))
        logger.info(
            "shoonya_order_placed",
            broker_id=broker_id,
            symbol=str(order.symbol),
        )
        return broker_id

    @_broker_retry
    async def cancel_order(self, broker_order_id: str) -> bool:
        payload = {**self._auth_payload(), "norenordno": broker_order_id}
        # Shoonya returns 200 OK even for logical failures, check "stat" field
        try:
            resp = await self._client.post("/CancelOrder", json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError:
             # Retry on actual HTTP errors
             raise 
             
        data = resp.json()
        if data.get("stat") == "Ok":
            logger.info("shoonya_order_cancelled", broker_id=broker_order_id)
            return True
        logger.warning("shoonya_cancel_failed", broker_id=broker_order_id, resp=data)
        return False

    @_broker_retry
    async def get_positions(self) -> list[dict[str, Any]]:
        payload = {**self._auth_payload(), "actid": self._user_id}
        resp = await self._client.post("/PositionBook", json=payload)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        return []

    @_broker_retry
    async def get_order_status(self, broker_order_id: str) -> dict[str, Any]:
        payload = {**self._auth_payload(), "norenordno": broker_order_id}
        resp = await self._client.post("/SingleOrderHistory", json=payload)
        resp.raise_for_status()
        return resp.json()

    @_broker_retry
    async def get_option_chain(self, symbol: str, expiry: str) -> dict[str, Any]:
        payload = {
            **self._auth_payload(),
            "exch": "NFO",
            "symbol": symbol,
            "expiry": expiry,
        }
        resp = await self._client.post("/GetOptionChain", json=payload)
        resp.raise_for_status()
        return resp.json()

    @_broker_retry
    async def get_historical_data(
        self, symbol: str, interval: str, from_date: datetime, to_date: datetime
    ) -> list[dict[str, Any]]:
        payload = {
            **self._auth_payload(),
            "exch": "NSE",  # Default to NSE for now
            "token": symbol, # Shoonya uses token, needs lookup
            "st": from_date.strftime("%s"), # Unix timestamp
            "et": to_date.strftime("%s"),
            "intrv": interval, # 1, 3, 5, 10, 15, 30, 60, etc.
        }
        resp = await self._client.post("/TPSeries", json=payload)
        resp.raise_for_status()
        data = resp.json()
        
        # Shoonya returns list of dicts naturally, but keys might differ
        # { "time": "...", "into": "...", "inth": "...", "intl": "...", "intc": "...", "intv": "..." }
        if isinstance(data, list):
            return [
                {
                    "timestamp": c.get("time"),
                    "open": float(c.get("into", 0)),
                    "high": float(c.get("inth", 0)),
                    "low": float(c.get("intl", 0)),
                    "close": float(c.get("intc", 0)),
                    "volume": int(c.get("intv", 0)),
                }
                for c in data
            ]
        return []

    async def close(self) -> None:
        await self._client.aclose()
