"""Order guardrails — sanity-check layer for AI-generated orders.

Guardrails intercept every order *before* the risk engine and perform
fast, cheap sanity checks that catch obviously malformed or suspicious
orders coming from LLM agents.
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass
from decimal import Decimal

from app.domain.entities import Order
from app.domain.enums import OrderType
from app.domain.value_objects import Money

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class GuardrailConfig:
    """Configurable thresholds for order sanity checks."""

    max_price_deviation_pct: float = 10.0  # reject if price deviates > 10% from ref
    min_order_price: Money = Money(Decimal("0.05"))
    max_order_price: Money = Money(Decimal("100000"))
    min_quantity: int = 1
    max_quantity: int = 5000


@dataclass(frozen=True, slots=True)
class GuardrailResult:
    passed: bool
    violations: list[str]

    @classmethod
    def ok(cls) -> GuardrailResult:
        return cls(passed=True, violations=[])

    @classmethod
    def fail(cls, violations: list[str]) -> GuardrailResult:
        return cls(passed=False, violations=violations)


class OrderGuardrails:
    """Fast sanity-check layer before risk evaluation.

    These checks catch obviously malformed orders that would indicate
    an LLM hallucination or prompt injection attempt.
    """

    def __init__(self, config: GuardrailConfig | None = None) -> None:
        self._config = config or GuardrailConfig()

    def check(
        self,
        order: Order,
        reference_price: Money | None = None,
    ) -> GuardrailResult:
        violations: list[str] = []

        # ── Quantity sanity ──────────────────────────────────
        if order.quantity.value < self._config.min_quantity:
            violations.append(
                f"Quantity {order.quantity.value} below minimum {self._config.min_quantity}"
            )
        if order.quantity.value > self._config.max_quantity:
            violations.append(
                f"Quantity {order.quantity.value} exceeds maximum {self._config.max_quantity}"
            )

        # ── Price sanity ─────────────────────────────────────
        if order.order_type != OrderType.MARKET:
            if order.price < self._config.min_order_price:
                violations.append(
                    f"Price {order.price.amount} below minimum {self._config.min_order_price.amount}"
                )
            if order.price > self._config.max_order_price:
                violations.append(
                    f"Price {order.price.amount} exceeds maximum {self._config.max_order_price.amount}"
                )

        # ── Price deviation from reference ───────────────────
        if reference_price and order.order_type != OrderType.MARKET:
            if reference_price.amount > 0:
                deviation_pct = abs(
                    float(
                        (order.price.amount - reference_price.amount)
                        / reference_price.amount
                        * 100
                    )
                )
                if deviation_pct > self._config.max_price_deviation_pct:
                    violations.append(
                        f"Price deviation {deviation_pct:.1f}% exceeds max "
                        f"{self._config.max_price_deviation_pct}%"
                    )

        # ── Symbol sanity ────────────────────────────────────
        if not order.symbol.value:
            violations.append("Order symbol is empty")

        if violations:
            logger.warning(
                "guardrail_violations",
                order_id=order.id,
                violations=violations,
            )
            return GuardrailResult.fail(violations)

        logger.debug("guardrail_passed", order_id=order.id)
        return GuardrailResult.ok()
