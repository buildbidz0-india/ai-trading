"""Unit tests for domain services — risk engine and guardrails."""

from __future__ import annotations

import pytest
from decimal import Decimal

from app.domain.entities import Order, Position
from app.domain.enums import OrderSide, OrderType
from app.domain.exceptions import KillSwitchActivatedError
from app.domain.services.guardrails import GuardrailConfig, OrderGuardrails
from app.domain.services.risk_engine import RiskEngine, RiskLimits
from app.domain.value_objects import Greeks, Money, Quantity, Symbol


# ═══════════════════════════════════════════════════════════════
#  Risk Engine
# ═══════════════════════════════════════════════════════════════
class TestRiskEngine:
    @pytest.fixture
    def engine(self):
        return RiskEngine(
            RiskLimits(
                max_order_value=Money(Decimal("500000")),
                max_position_delta=100.0,
                max_orders_per_minute=10,
                kill_switch_drawdown_pct=5.0,
                max_single_lot_count=20,
                max_open_positions=10,
            )
        )

    def test_accept_valid_order(self, engine, sample_order):
        verdict = engine.evaluate_order(
            order=sample_order,
            open_positions=[],
            recent_order_count=0,
            account_drawdown_pct=0.0,
        )
        assert verdict.accepted

    def test_reject_excessive_value(self, engine):
        order = Order(
            quantity=Quantity(5000, lot_size=50),
            price=Money(Decimal("200")),
        )
        verdict = engine.evaluate_order(
            order=order,
            open_positions=[],
            recent_order_count=0,
            account_drawdown_pct=0.0,
        )
        assert not verdict.accepted
        assert "exceeds max" in verdict.reason

    def test_reject_excessive_lot_count(self, engine):
        order = Order(
            quantity=Quantity(1100, lot_size=50),  # 22 lots
            price=Money(Decimal("1")),
        )
        verdict = engine.evaluate_order(
            order=order,
            open_positions=[],
            recent_order_count=0,
            account_drawdown_pct=0.0,
        )
        assert not verdict.accepted
        assert "Lot count" in verdict.reason

    def test_reject_rate_limit(self, engine, sample_order):
        verdict = engine.evaluate_order(
            order=sample_order,
            open_positions=[],
            recent_order_count=15,
            account_drawdown_pct=0.0,
        )
        assert not verdict.accepted
        assert "rate" in verdict.reason.lower()

    def test_reject_delta_exposure(self, engine, sample_order):
        positions = [
            Position(greeks=Greeks(delta=60.0)),
            Position(greeks=Greeks(delta=50.0)),
        ]
        verdict = engine.evaluate_order(
            order=sample_order,
            open_positions=positions,
            recent_order_count=0,
            account_drawdown_pct=0.0,
        )
        assert not verdict.accepted
        assert "delta" in verdict.reason.lower()

    def test_reject_too_many_positions(self, engine, sample_order):
        positions = [Position() for _ in range(10)]
        verdict = engine.evaluate_order(
            order=sample_order,
            open_positions=positions,
            recent_order_count=0,
            account_drawdown_pct=0.0,
        )
        assert not verdict.accepted

    def test_kill_switch_raises(self, engine, sample_order):
        with pytest.raises(KillSwitchActivatedError):
            engine.evaluate_order(
                order=sample_order,
                open_positions=[],
                recent_order_count=0,
                account_drawdown_pct=6.0,
            )


# ═══════════════════════════════════════════════════════════════
#  Guardrails
# ═══════════════════════════════════════════════════════════════
class TestGuardrails:
    @pytest.fixture
    def guardrails(self):
        return OrderGuardrails(GuardrailConfig())

    def test_valid_order_passes(self, guardrails, sample_order):
        result = guardrails.check(sample_order)
        assert result.passed
        assert len(result.violations) == 0

    def test_excessive_quantity(self, guardrails):
        order = Order(quantity=Quantity(6000, lot_size=1))
        result = guardrails.check(order)
        assert not result.passed
        assert any("exceeds maximum" in v for v in result.violations)

    def test_price_too_high(self, guardrails):
        order = Order(
            order_type=OrderType.LIMIT,
            price=Money(Decimal("200000")),
            quantity=Quantity(50, lot_size=50),
        )
        result = guardrails.check(order)
        assert not result.passed

    def test_price_deviation(self, guardrails, sample_order):
        ref_price = Money(Decimal("100"))
        # sample_order has price=150, deviation = 50% from 100
        result = guardrails.check(sample_order, reference_price=ref_price)
        assert not result.passed
        assert any("deviation" in v.lower() for v in result.violations)

    def test_market_order_skips_price_checks(self, guardrails):
        order = Order(
            order_type=OrderType.MARKET,
            quantity=Quantity(50, lot_size=50),
        )
        result = guardrails.check(order)
        assert result.passed
