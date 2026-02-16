"""Domain-specific exception hierarchy.

All exceptions inherit from ``DomainError`` so callers can catch the entire
family in one clause while still discriminating on subclass.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain-layer errors."""

    def __init__(self, message: str, *, code: str = "DOMAIN_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


# ── Validation ───────────────────────────────────────────────
class ValidationError(DomainError):
    """Input failed domain validation rules."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="VALIDATION_ERROR")


# ── Order ────────────────────────────────────────────────────
class OrderError(DomainError):
    """Base for order-related errors."""


class InvalidOrderTransitionError(OrderError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            f"Cannot transition order from {current!r} to {target!r}",
            code="INVALID_ORDER_TRANSITION",
        )


class OrderNotFoundError(OrderError):
    def __init__(self, order_id: str) -> None:
        super().__init__(f"Order {order_id!r} not found", code="ORDER_NOT_FOUND")


# ── Risk / Guardrails ───────────────────────────────────────
class RiskLimitExceededError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="RISK_LIMIT_EXCEEDED")


class KillSwitchActivatedError(DomainError):
    def __init__(self, drawdown_pct: float) -> None:
        super().__init__(
            f"Kill switch activated — drawdown {drawdown_pct:.2f}% exceeds threshold",
            code="KILL_SWITCH_ACTIVATED",
        )


# ── External services ───────────────────────────────────────
class BrokerError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="BROKER_ERROR")


class LLMError(DomainError):
    def __init__(self, provider: str, message: str) -> None:
        super().__init__(f"[{provider}] {message}", code="LLM_ERROR")


# ── Auth ─────────────────────────────────────────────────────
class AuthenticationError(DomainError):
    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, code="AUTHENTICATION_ERROR")


class AuthorisationError(DomainError):
    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message, code="AUTHORISATION_ERROR")
