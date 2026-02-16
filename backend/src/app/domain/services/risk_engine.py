"""Risk engine — deterministic, pre-trade validation.

The risk engine is a *pure domain service* with zero external dependencies.
It evaluates an order against current portfolio state and hard-coded limits,
returning an ``accept`` / ``reject`` verdict.
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass
from decimal import Decimal

from app.domain.entities import Order, Position
from app.domain.exceptions import KillSwitchActivatedError, RiskLimitExceededError
from app.domain.value_objects import Money

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RiskLimits:
    """Hard-coded risk parameters — loaded from config, never from AI."""

    max_order_value: Money = Money(Decimal("500000"))
    max_position_delta: float = 100.0
    max_orders_per_minute: int = 10
    kill_switch_drawdown_pct: float = 5.0
    max_single_lot_count: int = 20
    max_open_positions: int = 10


@dataclass(frozen=True, slots=True)
class RiskVerdict:
    """Result of a pre-trade risk check."""

    accepted: bool
    reason: str = ""

    @classmethod
    def accept(cls) -> RiskVerdict:
        return cls(accepted=True, reason="All risk checks passed")

    @classmethod
    def reject(cls, reason: str) -> RiskVerdict:
        return cls(accepted=False, reason=reason)


class RiskEngine:
    """Stateless pre-trade risk validator.

    Every AI-generated and manual order **must** pass through the risk engine
    before submission to the broker.  The engine is intentionally deterministic
    (no AI/ML) — it is the last line of defence.
    """

    def __init__(self, limits: RiskLimits) -> None:
        self._limits = limits

    def evaluate_order(
        self,
        order: Order,
        open_positions: list[Position],
        recent_order_count: int,
        account_drawdown_pct: float,
    ) -> RiskVerdict:
        """Run all pre-trade checks and return a verdict."""
        checks = [
            self._check_order_value(order),
            self._check_lot_count(order),
            self._check_order_rate(recent_order_count),
            self._check_delta_exposure(order, open_positions),
            self._check_position_count(open_positions),
            self._check_kill_switch(account_drawdown_pct),
        ]

        for verdict in checks:
            if not verdict.accepted:
                logger.warning(
                    "risk_check_failed",
                    order_id=order.id,
                    reason=verdict.reason,
                )
                return verdict

        logger.info("risk_check_passed", order_id=order.id)
        return RiskVerdict.accept()

    # ── Individual checks ────────────────────────────────────

    def _check_order_value(self, order: Order) -> RiskVerdict:
        if order.notional_value > self._limits.max_order_value:
            return RiskVerdict.reject(
                f"Order value {order.notional_value.amount} exceeds max "
                f"{self._limits.max_order_value.amount}"
            )
        return RiskVerdict.accept()

    def _check_lot_count(self, order: Order) -> RiskVerdict:
        if order.quantity.lots > self._limits.max_single_lot_count:
            return RiskVerdict.reject(
                f"Lot count {order.quantity.lots} exceeds max "
                f"{self._limits.max_single_lot_count}"
            )
        return RiskVerdict.accept()

    def _check_order_rate(self, recent_order_count: int) -> RiskVerdict:
        if recent_order_count >= self._limits.max_orders_per_minute:
            return RiskVerdict.reject(
                f"Order rate {recent_order_count}/min exceeds max "
                f"{self._limits.max_orders_per_minute}/min"
            )
        return RiskVerdict.accept()

    def _check_delta_exposure(
        self,
        order: Order,
        open_positions: list[Position],
    ) -> RiskVerdict:
        total_delta = sum(abs(p.greeks.delta) for p in open_positions)
        if total_delta > self._limits.max_position_delta:
            return RiskVerdict.reject(
                f"Portfolio delta {total_delta:.2f} exceeds max "
                f"{self._limits.max_position_delta}"
            )
        return RiskVerdict.accept()

    def _check_position_count(self, open_positions: list[Position]) -> RiskVerdict:
        if len(open_positions) >= self._limits.max_open_positions:
            return RiskVerdict.reject(
                f"Open positions {len(open_positions)} at max "
                f"{self._limits.max_open_positions}"
            )
        return RiskVerdict.accept()

    def _check_kill_switch(self, account_drawdown_pct: float) -> RiskVerdict:
        if account_drawdown_pct >= self._limits.kill_switch_drawdown_pct:
            raise KillSwitchActivatedError(account_drawdown_pct)
        return RiskVerdict.accept()
