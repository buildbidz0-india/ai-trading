"""Domain entities — objects with identity and lifecycle.

Entities are *mutable* but expose controlled mutation methods that enforce
business invariants.  They carry a unique ``id`` field.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from app.domain.enums import (
    Exchange,
    InstrumentType,
    OptionType,
    OrderSide,
    OrderStatus,
    OrderType,
    ProductType,
)
from app.domain.exceptions import InvalidOrderTransitionError
from app.domain.value_objects import Expiry, Greeks, Money, Quantity, StrikePrice, Symbol

if TYPE_CHECKING:
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


# ═══════════════════════════════════════════════════════════════
#  Instrument
# ═══════════════════════════════════════════════════════════════
@dataclass(slots=True)
class Instrument:
    """Tradeable instrument descriptor (equity, future, or option)."""

    id: str = field(default_factory=_new_id)
    symbol: Symbol = field(default_factory=lambda: Symbol("NIFTY"))
    exchange: Exchange = Exchange.NFO
    instrument_type: InstrumentType = InstrumentType.INDEX
    lot_size: int = 50
    tick_size: Decimal = Decimal("0.05")

    # Option-specific (None for non-options)
    option_type: OptionType | None = None
    strike_price: StrikePrice | None = None
    expiry: Expiry | None = None

    @property
    def is_option(self) -> bool:
        return self.instrument_type in (
            InstrumentType.CALL_OPTION,
            InstrumentType.PUT_OPTION,
        )

    @property
    def display_name(self) -> str:
        parts = [str(self.symbol), self.exchange.value]
        if self.expiry:
            parts.append(self.expiry.date.strftime("%d%b%y").upper())
        if self.strike_price:
            parts.append(str(self.strike_price.value))
        if self.option_type:
            parts.append(self.option_type.value)
        return " ".join(parts)


# ═══════════════════════════════════════════════════════════════
#  Order
# ═══════════════════════════════════════════════════════════════
@dataclass(slots=True)
class Order:
    """Trade order with FSM-based lifecycle management."""

    id: str = field(default_factory=_new_id)
    instrument_id: str = ""
    symbol: Symbol = field(default_factory=lambda: Symbol("NIFTY"))
    exchange: Exchange = Exchange.NFO
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    product_type: ProductType = ProductType.NRML
    quantity: Quantity = field(default_factory=lambda: Quantity(50, lot_size=50))
    price: Money = field(default_factory=Money.zero)
    trigger_price: Money = field(default_factory=Money.zero)
    status: OrderStatus = OrderStatus.PENDING_VALIDATION

    # Metadata
    broker_order_id: str | None = None
    idempotency_key: str = field(default_factory=_new_id)
    source: str = "SYSTEM"  # SYSTEM | AI_AGENT | MANUAL
    rejection_reason: str | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    # ── State transitions ────────────────────────────────────
    def transition_to(self, new_status: OrderStatus, reason: str | None = None) -> None:
        if not self.status.can_transition_to(new_status):
            raise InvalidOrderTransitionError(self.status.value, new_status.value)
        self.status = new_status
        self.updated_at = _utcnow()
        if new_status == OrderStatus.REJECTED and reason:
            self.rejection_reason = reason

    def validate(self) -> None:
        self.transition_to(OrderStatus.VALIDATED)

    def reject(self, reason: str) -> None:
        self.transition_to(OrderStatus.REJECTED, reason=reason)

    def submit(self, broker_order_id: str) -> None:
        self.broker_order_id = broker_order_id
        self.transition_to(OrderStatus.SUBMITTED)

    def fill(self) -> None:
        if self.status == OrderStatus.SUBMITTED:
            self.transition_to(OrderStatus.OPEN)
        self.transition_to(OrderStatus.FILLED)

    def cancel(self) -> None:
        self.transition_to(OrderStatus.CANCELLED)

    @property
    def notional_value(self) -> Money:
        return self.price * self.quantity.value


# ═══════════════════════════════════════════════════════════════
#  Trade
# ═══════════════════════════════════════════════════════════════
@dataclass(slots=True)
class Trade:
    """Executed trade record — immutable after creation."""

    id: str = field(default_factory=_new_id)
    order_id: str = ""
    instrument_id: str = ""
    symbol: Symbol = field(default_factory=lambda: Symbol("NIFTY"))
    exchange: Exchange = Exchange.NFO
    side: OrderSide = OrderSide.BUY
    quantity: Quantity = field(default_factory=lambda: Quantity(50, lot_size=50))
    price: Money = field(default_factory=Money.zero)
    fees: Money = field(default_factory=Money.zero)
    executed_at: datetime = field(default_factory=_utcnow)

    @property
    def net_value(self) -> Money:
        """Total cost/proceeds after fees."""
        base = self.price * self.quantity.value
        if self.side == OrderSide.BUY:
            return base + self.fees
        return base - self.fees


# ═══════════════════════════════════════════════════════════════
#  Position
# ═══════════════════════════════════════════════════════════════
@dataclass(slots=True)
class Position:
    """Aggregate position for a single instrument."""

    id: str = field(default_factory=_new_id)
    instrument_id: str = ""
    symbol: Symbol = field(default_factory=lambda: Symbol("NIFTY"))
    exchange: Exchange = Exchange.NFO

    # Net position
    net_quantity: int = 0  # positive = long, negative = short
    average_price: Money = field(default_factory=Money.zero)
    realised_pnl: Money = field(default_factory=Money.zero)
    unrealised_pnl: Money = field(default_factory=Money.zero)

    # Greeks exposure
    greeks: Greeks = field(default_factory=Greeks.zero)

    updated_at: datetime = field(default_factory=_utcnow)

    @property
    def is_open(self) -> bool:
        return self.net_quantity != 0

    @property
    def is_long(self) -> bool:
        return self.net_quantity > 0

    @property
    def is_short(self) -> bool:
        return self.net_quantity < 0

    def apply_trade(self, trade: Trade) -> None:
        """Update position from a new trade."""
        signed_qty = trade.quantity.value if trade.side == OrderSide.BUY else -trade.quantity.value
        self.net_quantity += signed_qty
        self.updated_at = _utcnow()


# ═══════════════════════════════════════════════════════════════
#  OptionChainSnapshot
# ═══════════════════════════════════════════════════════════════
@dataclass(slots=True)
class OptionChainEntry:
    """Single row in the option chain (one strike)."""

    strike_price: StrikePrice
    call_price: Money = field(default_factory=Money.zero)
    put_price: Money = field(default_factory=Money.zero)
    call_oi: int = 0
    put_oi: int = 0
    call_volume: int = 0
    put_volume: int = 0
    call_greeks: Greeks = field(default_factory=Greeks.zero)
    put_greeks: Greeks = field(default_factory=Greeks.zero)
    call_iv: float = 0.0
    put_iv: float = 0.0


@dataclass(slots=True)
class OptionChainSnapshot:
    """Point-in-time snapshot of the full option chain."""

    symbol: Symbol
    expiry: Expiry
    underlying_price: Money
    entries: list[OptionChainEntry] = field(default_factory=list)
    timestamp: datetime = field(default_factory=_utcnow)

    @property
    def max_pain(self) -> StrikePrice | None:
        """Calculate the max pain strike (strike with minimum total OI-weighted loss)."""
        if not self.entries:
            return None
        # Simplified max pain: strike with maximum total OI
        best = max(self.entries, key=lambda e: e.call_oi + e.put_oi)
        return best.strike_price
