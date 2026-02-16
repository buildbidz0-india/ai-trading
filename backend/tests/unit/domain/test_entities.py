"""Unit tests for domain entities."""

from __future__ import annotations

import pytest
from decimal import Decimal

from app.domain.entities import (
    Instrument,
    OptionChainEntry,
    OptionChainSnapshot,
    Order,
    Position,
    Trade,
)
from app.domain.enums import (
    Exchange,
    InstrumentType,
    OrderSide,
    OrderStatus,
    OrderType,
    ProductType,
)
from app.domain.exceptions import InvalidOrderTransitionError
from app.domain.value_objects import (
    Expiry,
    Greeks,
    Money,
    Quantity,
    StrikePrice,
    Symbol,
)
from datetime import date


# ── Order FSM ────────────────────────────────────────────────
class TestOrder:
    def test_initial_status(self):
        order = Order()
        assert order.status == OrderStatus.PENDING_VALIDATION

    def test_validate_transition(self, sample_order):
        sample_order.validate()
        assert sample_order.status == OrderStatus.VALIDATED

    def test_reject_transition(self, sample_order):
        sample_order.reject("Too risky")
        assert sample_order.status == OrderStatus.REJECTED
        assert sample_order.rejection_reason == "Too risky"

    def test_full_lifecycle(self, sample_order):
        sample_order.validate()
        sample_order.submit("BROKER-123")
        assert sample_order.broker_order_id == "BROKER-123"
        assert sample_order.status == OrderStatus.SUBMITTED

    def test_invalid_transition_raises(self, sample_order):
        sample_order.validate()
        with pytest.raises(InvalidOrderTransitionError):
            sample_order.validate()  # can't go VALIDATED -> VALIDATED

    def test_fill_from_submitted(self, sample_order):
        sample_order.validate()
        sample_order.submit("B-1")
        sample_order.fill()
        assert sample_order.status == OrderStatus.FILLED

    def test_cancel_from_open(self, sample_order):
        sample_order.validate()
        sample_order.submit("B-2")
        sample_order.transition_to(OrderStatus.OPEN)
        sample_order.cancel()
        assert sample_order.status == OrderStatus.CANCELLED

    def test_notional_value(self, sample_order):
        nv = sample_order.notional_value
        assert nv.amount == Decimal("7500.00")  # 150 * 50


# ── Trade ────────────────────────────────────────────────────
class TestTrade:
    def test_net_value_buy(self):
        trade = Trade(
            side=OrderSide.BUY,
            quantity=Quantity(50, lot_size=50),
            price=Money(Decimal("100")),
            fees=Money(Decimal("10")),
        )
        assert trade.net_value.amount == Decimal("5010")  # 100*50 + 10

    def test_net_value_sell(self):
        trade = Trade(
            side=OrderSide.SELL,
            quantity=Quantity(50, lot_size=50),
            price=Money(Decimal("100")),
            fees=Money(Decimal("10")),
        )
        assert trade.net_value.amount == Decimal("4990")  # 100*50 - 10


# ── Position ─────────────────────────────────────────────────
class TestPosition:
    def test_is_open(self, sample_position):
        assert sample_position.is_open
        assert sample_position.is_long

    def test_is_short(self):
        pos = Position(net_quantity=-50)
        assert pos.is_short
        assert pos.is_open

    def test_flat_position(self):
        pos = Position(net_quantity=0)
        assert not pos.is_open

    def test_apply_trade(self, sample_position):
        trade = Trade(
            side=OrderSide.BUY,
            quantity=Quantity(50, lot_size=50),
            price=Money(Decimal("155")),
        )
        sample_position.apply_trade(trade)
        assert sample_position.net_quantity == 150

    def test_apply_sell_trade(self, sample_position):
        trade = Trade(
            side=OrderSide.SELL,
            quantity=Quantity(50, lot_size=50),
            price=Money(Decimal("160")),
        )
        sample_position.apply_trade(trade)
        assert sample_position.net_quantity == 50


# ── Instrument ───────────────────────────────────────────────
class TestInstrument:
    def test_display_name(self, sample_instrument):
        assert "NIFTY" in sample_instrument.display_name

    def test_is_option(self, sample_instrument):
        assert sample_instrument.is_option


# ── OptionChainSnapshot ─────────────────────────────────────
class TestOptionChainSnapshot:
    def test_max_pain(self):
        snap = OptionChainSnapshot(
            symbol=Symbol("NIFTY"),
            expiry=Expiry(date(2025, 12, 25)),
            underlying_price=Money(Decimal("21000")),
            entries=[
                OptionChainEntry(
                    strike_price=StrikePrice(Decimal("20900")),
                    call_oi=1000,
                    put_oi=500,
                ),
                OptionChainEntry(
                    strike_price=StrikePrice(Decimal("21000")),
                    call_oi=5000,
                    put_oi=5000,
                ),
                OptionChainEntry(
                    strike_price=StrikePrice(Decimal("21100")),
                    call_oi=300,
                    put_oi=200,
                ),
            ],
        )
        assert snap.max_pain is not None
        assert snap.max_pain.value == Decimal("21000")

    def test_empty_chain_max_pain(self):
        snap = OptionChainSnapshot(
            symbol=Symbol("NIFTY"),
            expiry=Expiry(date(2025, 12, 25)),
            underlying_price=Money(Decimal("21000")),
        )
        assert snap.max_pain is None
