"""Unit tests for domain value objects."""

from __future__ import annotations

import pytest
from datetime import date
from decimal import Decimal

from app.domain.value_objects import (
    Expiry,
    Greeks,
    Money,
    Quantity,
    StrikePrice,
    Symbol,
)


# ── Money ────────────────────────────────────────────────────
class TestMoney:
    def test_creation_from_decimal(self):
        m = Money(Decimal("100.50"))
        assert m.amount == Decimal("100.50")
        assert m.currency == "INR"

    def test_creation_from_int(self):
        m = Money(100)
        assert m.amount == Decimal("100")

    def test_addition(self):
        result = Money(Decimal("100")) + Money(Decimal("50"))
        assert result.amount == Decimal("150")

    def test_subtraction(self):
        result = Money(Decimal("100")) - Money(Decimal("30"))
        assert result.amount == Decimal("70")

    def test_multiplication(self):
        result = Money(Decimal("100")) * 3
        assert result.amount == Decimal("300")

    def test_comparison(self):
        assert Money(Decimal("100")) > Money(Decimal("50"))
        assert Money(Decimal("50")) < Money(Decimal("100"))
        assert Money(Decimal("100")) >= Money(Decimal("100"))
        assert Money(Decimal("100")) <= Money(Decimal("100"))

    def test_currency_mismatch_raises(self):
        with pytest.raises(ValueError, match="Currency mismatch"):
            Money(Decimal("100"), "INR") + Money(Decimal("50"), "USD")

    def test_zero(self):
        assert Money.zero().amount == Decimal("0")

    def test_from_str(self):
        m = Money.from_str("123.45")
        assert m.amount == Decimal("123.45")

    def test_from_str_invalid(self):
        with pytest.raises(ValueError, match="Invalid monetary amount"):
            Money.from_str("not-a-number")

    def test_rounded(self):
        m = Money(Decimal("100.456789"))
        assert m.rounded(2).amount == Decimal("100.46")

    def test_negation(self):
        m = -Money(Decimal("100"))
        assert m.amount == Decimal("-100")

    def test_abs(self):
        m = abs(Money(Decimal("-100")))
        assert m.amount == Decimal("100")


# ── Symbol ───────────────────────────────────────────────────
class TestSymbol:
    def test_valid_symbol(self):
        s = Symbol("NIFTY")
        assert s.value == "NIFTY"

    def test_lowercase_uppercased(self):
        s = Symbol("nifty")
        assert s.value == "NIFTY"

    def test_symbol_with_numbers(self):
        s = Symbol("NIFTY50")
        assert s.value == "NIFTY50"

    def test_invalid_symbol_raises(self):
        with pytest.raises(ValueError, match="Invalid symbol"):
            Symbol("123")

    def test_empty_symbol_raises(self):
        with pytest.raises(ValueError):
            Symbol("")

    def test_str_representation(self):
        assert str(Symbol("RELIANCE")) == "RELIANCE"


# ── Greeks ───────────────────────────────────────────────────
class TestGreeks:
    def test_zero(self):
        g = Greeks.zero()
        assert g.delta == 0.0
        assert g.gamma == 0.0

    def test_addition(self):
        g1 = Greeks(delta=0.5, gamma=0.01, theta=-5.0, vega=10.0, rho=0.1)
        g2 = Greeks(delta=0.3, gamma=0.02, theta=-3.0, vega=8.0, rho=0.05)
        result = g1 + g2
        assert result.delta == pytest.approx(0.8)
        assert result.gamma == pytest.approx(0.03)
        assert result.theta == pytest.approx(-8.0)

    def test_multiplication(self):
        g = Greeks(delta=0.5, gamma=0.01, theta=-5.0, vega=10.0, rho=0.1)
        result = g * 2
        assert result.delta == pytest.approx(1.0)
        assert result.vega == pytest.approx(20.0)


# ── Quantity ─────────────────────────────────────────────────
class TestQuantity:
    def test_valid_quantity(self):
        q = Quantity(100, lot_size=50)
        assert q.value == 100
        assert q.lots == 2

    def test_not_multiple_of_lot_size(self):
        with pytest.raises(ValueError, match="not a multiple"):
            Quantity(75, lot_size=50)

    def test_negative_quantity(self):
        with pytest.raises(ValueError, match="must be positive"):
            Quantity(-50, lot_size=50)

    def test_zero_quantity(self):
        with pytest.raises(ValueError, match="must be positive"):
            Quantity(0, lot_size=50)


# ── StrikePrice ──────────────────────────────────────────────
class TestStrikePrice:
    def test_valid(self):
        sp = StrikePrice(Decimal("21000"))
        assert sp.value == Decimal("21000")

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="must be positive"):
            StrikePrice(Decimal("-100"))

    def test_from_int(self):
        sp = StrikePrice(21000)
        assert sp.value == Decimal("21000")


# ── Expiry ───────────────────────────────────────────────────
class TestExpiry:
    def test_days_to_expiry(self):
        future = date(2099, 12, 31)
        e = Expiry(future)
        assert e.days_to_expiry() > 0
        assert not e.is_expired

    def test_expired(self):
        past = date(2020, 1, 1)
        e = Expiry(past)
        assert e.is_expired
        assert e.days_to_expiry() == 0
