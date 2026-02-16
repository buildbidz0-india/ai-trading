"""Domain events — typed records of things that happened in the domain.

Events are published *after* a successful domain operation so that other
bounded contexts or infrastructure adapters can react asynchronously.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Base class for all domain events."""

    event_type: str = "DOMAIN_EVENT"
    occurred_at: datetime = field(default_factory=_utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Order events ─────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class OrderPlacedEvent(DomainEvent):
    event_type: str = "ORDER_PLACED"
    order_id: str = ""
    symbol: str = ""
    side: str = ""
    quantity: int = 0
    price: str = "0"


@dataclass(frozen=True, slots=True)
class OrderRejectedEvent(DomainEvent):
    event_type: str = "ORDER_REJECTED"
    order_id: str = ""
    reason: str = ""


@dataclass(frozen=True, slots=True)
class OrderFilledEvent(DomainEvent):
    event_type: str = "ORDER_FILLED"
    order_id: str = ""
    trade_id: str = ""
    fill_price: str = "0"
    fill_quantity: int = 0


@dataclass(frozen=True, slots=True)
class OrderCancelledEvent(DomainEvent):
    event_type: str = "ORDER_CANCELLED"
    order_id: str = ""


# ── Position events ──────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class PositionUpdatedEvent(DomainEvent):
    event_type: str = "POSITION_UPDATED"
    position_id: str = ""
    symbol: str = ""
    net_quantity: int = 0
    unrealised_pnl: str = "0"


# ── Risk events ──────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class KillSwitchTriggeredEvent(DomainEvent):
    event_type: str = "KILL_SWITCH_TRIGGERED"
    drawdown_pct: float = 0.0
    action: str = "ALL_POSITIONS_CLOSED"


# ── AI agent events ──────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class AgentAnalysisCompletedEvent(DomainEvent):
    event_type: str = "AGENT_ANALYSIS_COMPLETED"
    agent_role: str = ""
    provider: str = ""
    confidence: float = 0.0
    latency_ms: float = 0.0
    summary: str = ""


# ── Market data events ───────────────────────────────────────
@dataclass(frozen=True, slots=True)
class TickReceivedEvent(DomainEvent):
    event_type: str = "TICK_RECEIVED"
    symbol: str = ""
    price: str = "0"
    volume: int = 0
