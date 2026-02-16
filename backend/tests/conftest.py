"""Shared test fixtures."""

from __future__ import annotations

import pytest
import sys
import os
import bcrypt
# Patch bcrypt for passlib compatibility
bcrypt.__about__ = type("about", (object,), {"__version__": bcrypt.__version__})

from decimal import Decimal

# Add src to path so imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from app.domain.entities import Instrument, Order, Position
from app.domain.enums import (
    Exchange,
    InstrumentType,
    OrderSide,
    OrderStatus,
    OrderType,
    ProductType,
)
from app.domain.value_objects import Greeks, Money, Quantity, Symbol


@pytest.fixture
def sample_order() -> Order:
    return Order(
        id="test-order-001",
        symbol=Symbol("NIFTY"),
        exchange=Exchange.NFO,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        product_type=ProductType.NRML,
        quantity=Quantity(50, lot_size=50),
        price=Money(Decimal("150.00")),
    )


@pytest.fixture
def sample_position() -> Position:
    return Position(
        id="test-pos-001",
        instrument_id="inst-001",
        symbol=Symbol("NIFTY"),
        exchange=Exchange.NFO,
        net_quantity=100,
        average_price=Money(Decimal("145.00")),
        greeks=Greeks(delta=0.5, gamma=0.01, theta=-5.0, vega=10.0),
    )


@pytest.fixture
def sample_instrument() -> Instrument:
    return Instrument(
        id="inst-001",
        symbol=Symbol("NIFTY"),
        exchange=Exchange.NFO,
        instrument_type=InstrumentType.CALL_OPTION,
        lot_size=50,
    )
