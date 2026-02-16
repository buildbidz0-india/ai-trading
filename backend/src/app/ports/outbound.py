"""Outbound ports — interfaces that infrastructure adapters must implement.

These are the *driven* ports in hexagonal architecture.  The domain and
application layers depend only on these abstractions, never on concrete
implementations (database drivers, HTTP clients, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.domain.entities import (
    Instrument,
    OptionChainSnapshot,
    Order,
    Position,
    Trade,
)
from app.domain.enums import LLMProvider, OrderStatus
from app.domain.events import DomainEvent
from app.domain.value_objects import Symbol


# ═══════════════════════════════════════════════════════════════
#  Repository ports
# ═══════════════════════════════════════════════════════════════
class OrderRepository(ABC):
    """Persistence for orders."""

    @abstractmethod
    async def save(self, order: Order) -> None: ...

    @abstractmethod
    async def get_by_id(self, order_id: str) -> Order | None: ...

    @abstractmethod
    async def list_by_status(
        self, status: OrderStatus, *, limit: int = 100
    ) -> list[Order]: ...

    @abstractmethod
    async def list_recent(
        self, *, since: datetime | None = None, limit: int = 100
    ) -> list[Order]: ...

    @abstractmethod
    async def count_since(self, since: datetime) -> int: ...

    @abstractmethod
    async def update(self, order: Order) -> None: ...


class TradeRepository(ABC):
    """Append-only trade log."""

    @abstractmethod
    async def save(self, trade: Trade) -> None: ...

    @abstractmethod
    async def get_by_id(self, trade_id: str) -> Trade | None: ...

    @abstractmethod
    async def list_by_order(self, order_id: str) -> list[Trade]: ...

    @abstractmethod
    async def list_recent(
        self, *, since: datetime | None = None, limit: int = 100
    ) -> list[Trade]: ...


class PositionRepository(ABC):
    """Current position state."""

    @abstractmethod
    async def save(self, position: Position) -> None: ...

    @abstractmethod
    async def get_by_instrument(self, instrument_id: str) -> Position | None: ...

    @abstractmethod
    async def list_open(self) -> list[Position]: ...

    @abstractmethod
    async def update(self, position: Position) -> None: ...


class InstrumentRepository(ABC):
    """Instrument catalogue."""

    @abstractmethod
    async def get_by_id(self, instrument_id: str) -> Instrument | None: ...

    @abstractmethod
    async def get_by_symbol(
        self, symbol: Symbol, *, exchange: str | None = None
    ) -> list[Instrument]: ...

    @abstractmethod
    async def save(self, instrument: Instrument) -> None: ...

    @abstractmethod
    async def search(
        self, query: str, *, limit: int = 20
    ) -> list[Instrument]: ...


# ═══════════════════════════════════════════════════════════════
#  Cache port
# ═══════════════════════════════════════════════════════════════
class CachePort(ABC):
    """Key-value cache with pub/sub (backed by Redis)."""

    @abstractmethod
    async def get(self, key: str) -> str | None: ...

    @abstractmethod
    async def set(
        self, key: str, value: str, *, ttl_seconds: int | None = None
    ) -> None: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def publish(self, channel: str, message: str) -> None: ...

    @abstractmethod
    async def increment(self, key: str, *, ttl_seconds: int | None = None) -> int: ...


# ═══════════════════════════════════════════════════════════════
#  Broker port
# ═══════════════════════════════════════════════════════════════
class BrokerPort(ABC):
    """Broker API for order execution and position management."""

    @abstractmethod
    async def place_order(self, order: Order) -> str:
        """Submit order and return broker order ID."""
        ...

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> bool: ...

    @abstractmethod
    async def get_positions(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def get_order_status(self, broker_order_id: str) -> dict[str, Any]: ...

    @abstractmethod
    async def get_option_chain(self, symbol: str, expiry: str) -> dict[str, Any]: ...


# ═══════════════════════════════════════════════════════════════
#  Market data port
# ═══════════════════════════════════════════════════════════════
class MarketDataPort(ABC):
    """Live market data streaming."""

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def subscribe(self, symbols: list[str]) -> None: ...

    @abstractmethod
    async def unsubscribe(self, symbols: list[str]) -> None: ...


# ═══════════════════════════════════════════════════════════════
#  LLM port
# ═══════════════════════════════════════════════════════════════
class LLMPort(ABC):
    """Abstraction over LLM providers."""

    @abstractmethod
    async def invoke(
        self,
        *,
        provider: LLMProvider,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a prompt and return a structured response."""
        ...


# ═══════════════════════════════════════════════════════════════
#  Event bus port
# ═══════════════════════════════════════════════════════════════
class EventBusPort(ABC):
    """Publish/subscribe for domain events."""

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None: ...

    @abstractmethod
    def subscribe(
        self,
        event_type: str,
        handler: Any,
    ) -> None: ...
