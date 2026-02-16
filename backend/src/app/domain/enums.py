"""Domain enumerations for the trading platform."""

from __future__ import annotations

import enum


class OrderSide(str, enum.Enum):
    """Buy or sell."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, enum.Enum):
    """Limit, market, stop-loss, etc."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"


class OrderStatus(str, enum.Enum):
    """Lifecycle state machine for an order."""

    PENDING_VALIDATION = "PENDING_VALIDATION"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    SUBMITTED = "SUBMITTED"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"

    # ── Allowed transitions ──
    def can_transition_to(self, target: OrderStatus) -> bool:
        return target in _ORDER_TRANSITIONS.get(self, set())


_ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING_VALIDATION: {OrderStatus.VALIDATED, OrderStatus.REJECTED},
    OrderStatus.VALIDATED: {OrderStatus.SUBMITTED, OrderStatus.REJECTED},
    OrderStatus.SUBMITTED: {
        OrderStatus.OPEN,
        OrderStatus.FILLED,
        OrderStatus.FAILED,
        OrderStatus.REJECTED,
    },
    OrderStatus.OPEN: {
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCELLED,
        OrderStatus.EXPIRED,
    },
    OrderStatus.PARTIALLY_FILLED: {
        OrderStatus.FILLED,
        OrderStatus.CANCELLED,
    },
}


class ProductType(str, enum.Enum):
    """NSE product types."""

    CNC = "CNC"  # Cash & carry (delivery)
    MIS = "MIS"  # Margin intraday square-off
    NRML = "NRML"  # Normal (F&O carry-forward)


class Exchange(str, enum.Enum):
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"  # NSE F&O
    BFO = "BFO"  # BSE F&O
    MCX = "MCX"


class InstrumentType(str, enum.Enum):
    EQUITY = "EQUITY"
    FUTURE = "FUTURE"
    CALL_OPTION = "CE"
    PUT_OPTION = "PE"
    INDEX = "INDEX"


class OptionType(str, enum.Enum):
    CALL = "CE"
    PUT = "PE"


class AgentRole(str, enum.Enum):
    """AI agent specialisation roles."""

    MARKET_SENSOR = "MARKET_SENSOR"
    QUANT = "QUANT"
    EXECUTIONER = "EXECUTIONER"


class LLMProvider(str, enum.Enum):
    ANTHROPIC = "ANTHROPIC"
    GOOGLE = "GOOGLE"
    OPENAI = "OPENAI"
