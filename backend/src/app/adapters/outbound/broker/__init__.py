"""Broker adapters package.

Provides paper (simulation) and production broker adapters that
implement the ``BrokerPort`` interface.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from app.domain.entities import Order
from app.ports.outbound import BrokerPort

logger = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
#  Paper (simulation) broker
# ═══════════════════════════════════════════════════════════════
class PaperBrokerAdapter(BrokerPort):
    """Simulated broker for paper trading (Ghost Mode).

    All orders are "accepted" instantly with fake broker IDs.
    No real money is involved.
    """

    def __init__(self) -> None:
        self._orders: dict[str, dict[str, Any]] = {}
        self._positions: list[dict[str, Any]] = []

    async def place_order(self, order: Order) -> str:
        hex_val: str = uuid.uuid4().hex
        broker_id = f"PAPER-{hex_val[:8].upper()}"
        self._orders[broker_id] = {
            "broker_order_id": broker_id,
            "symbol": str(order.symbol),
            "side": order.side.value,
            "quantity": order.quantity.value,
            "price": str(order.price.amount),
            "status": "FILLED",
        }
        logger.info(
            "paper_order_placed",
            broker_id=broker_id,
            symbol=str(order.symbol),
            side=order.side.value,
        )
        return broker_id

    async def cancel_order(self, broker_order_id: str) -> bool:
        if broker_order_id in self._orders:
            self._orders[broker_order_id]["status"] = "CANCELLED"
            logger.info("paper_order_cancelled", broker_id=broker_order_id)
            return True
        return False

    async def get_positions(self) -> list[dict[str, Any]]:
        return self._positions

    async def get_order_status(self, broker_order_id: str) -> dict[str, Any]:
        return self._orders.get(broker_order_id, {"status": "UNKNOWN"})

    async def get_option_chain(self, symbol: str, expiry: str) -> dict[str, Any]:
        logger.info("paper_option_chain_request", symbol=symbol, expiry=expiry)
        return {"symbol": symbol, "expiry": expiry, "entries": []}


# ── Re-export production adapters ─────────────────────────────
from app.adapters.outbound.broker.dhan import DhanBrokerAdapter  # noqa: E402
from app.adapters.outbound.broker.shoonya import ShoonyaBrokerAdapter  # noqa: E402
from app.adapters.outbound.broker.zerodha import ZerodhaBrokerAdapter  # noqa: E402

__all__ = [
    "BrokerPort",
    "PaperBrokerAdapter",
    "DhanBrokerAdapter",
    "ZerodhaBrokerAdapter",
    "ShoonyaBrokerAdapter",
]

