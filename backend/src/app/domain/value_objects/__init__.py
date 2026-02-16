"""Domain value objects — immutable, self-validating types.

Value objects have *no identity*; two instances with equal fields are equal.
They enforce invariants at construction time so the rest of the domain can
trust their contents without re-checking.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation


# ═══════════════════════════════════════════════════════════════
#  Money
# ═══════════════════════════════════════════════════════════════
@dataclass(frozen=True, slots=True)
class Money:
    """Monetary amount with currency.  All arithmetic is Decimal-based."""

    amount: Decimal
    currency: str = "INR"

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))

    # ── Arithmetic ───────────────────────────────────────────
    def __add__(self, other: Money) -> Money:
        self._assert_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._assert_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: int | float | Decimal) -> Money:
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def __abs__(self) -> Money:
        return Money(abs(self.amount), self.currency)

    # ── Comparison ───────────────────────────────────────────
    def __lt__(self, other: Money) -> bool:
        self._assert_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        self._assert_same_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        self._assert_same_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        self._assert_same_currency(other)
        return self.amount >= other.amount

    # ── Helpers ──────────────────────────────────────────────
    @classmethod
    def zero(cls, currency: str = "INR") -> Money:
        return cls(Decimal("0"), currency)

    @classmethod
    def from_str(cls, raw: str, currency: str = "INR") -> Money:
        try:
            return cls(Decimal(raw), currency)
        except InvalidOperation as exc:
            raise ValueError(f"Invalid monetary amount: {raw!r}") from exc

    def rounded(self, places: int = 2) -> Money:
        return Money(round(self.amount, places), self.currency)

    def _assert_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(
                f"Currency mismatch: {self.currency} vs {other.currency}"
            )


# ═══════════════════════════════════════════════════════════════
#  Symbol
# ═══════════════════════════════════════════════════════════════
_SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9&\-]{0,29}$")


@dataclass(frozen=True, slots=True)
class Symbol:
    """Validated NSE/BSE trading symbol (e.g. ``NIFTY``, ``RELIANCE``)."""

    value: str

    def __post_init__(self) -> None:
        v = self.value.upper().strip()
        object.__setattr__(self, "value", v)
        if not _SYMBOL_RE.match(v):
            raise ValueError(f"Invalid symbol: {self.value!r}")

    def __str__(self) -> str:
        return self.value


# ═══════════════════════════════════════════════════════════════
#  Greeks
# ═══════════════════════════════════════════════════════════════
@dataclass(frozen=True, slots=True)
class Greeks:
    """Option greeks snapshot for a single leg or aggregated position."""

    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    rho: float = 0.0

    def __add__(self, other: Greeks) -> Greeks:
        return Greeks(
            delta=self.delta + other.delta,
            gamma=self.gamma + other.gamma,
            theta=self.theta + other.theta,
            vega=self.vega + other.vega,
            rho=self.rho + other.rho,
        )

    def __mul__(self, factor: int | float) -> Greeks:
        return Greeks(
            delta=self.delta * factor,
            gamma=self.gamma * factor,
            theta=self.theta * factor,
            vega=self.vega * factor,
            rho=self.rho * factor,
        )

    @classmethod
    def zero(cls) -> Greeks:
        return cls()


# ═══════════════════════════════════════════════════════════════
#  Quantity
# ═══════════════════════════════════════════════════════════════
@dataclass(frozen=True, slots=True)
class Quantity:
    """Lot-size-aware quantity (always a positive integer multiple of lot_size)."""

    value: int
    lot_size: int = 1

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError(f"Quantity must be positive, got {self.value}")
        if self.lot_size <= 0:
            raise ValueError(f"Lot size must be positive, got {self.lot_size}")
        if self.value % self.lot_size != 0:
            raise ValueError(
                f"Quantity {self.value} is not a multiple of lot size {self.lot_size}"
            )

    @property
    def lots(self) -> int:
        return self.value // self.lot_size


# ═══════════════════════════════════════════════════════════════
#  StrikePrice
# ═══════════════════════════════════════════════════════════════
@dataclass(frozen=True, slots=True)
class StrikePrice:
    """Validated option strike price."""

    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, "value", Decimal(str(self.value)))
        if self.value <= 0:
            raise ValueError(f"Strike price must be positive, got {self.value}")


# ═══════════════════════════════════════════════════════════════
#  Expiry
# ═══════════════════════════════════════════════════════════════
@dataclass(frozen=True, slots=True)
class Expiry:
    """Option/future expiry date."""

    date: date

    @property
    def is_expired(self) -> bool:
        from datetime import date as _date

        return self.date < _date.today()

    def days_to_expiry(self) -> int:
        from datetime import date as _date

        return max(0, (self.date - _date.today()).days)
