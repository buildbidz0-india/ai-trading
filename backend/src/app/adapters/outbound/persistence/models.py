"""SQLAlchemy ORM models for PostgreSQL / TimescaleDB.

These are *infrastructure* models — they map to database tables but are
separate from domain entities.  Converters translate between the two layers.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    instrument_id: Mapped[str] = mapped_column(String(32), nullable=True)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False)
    product_type: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    lot_size: Mapped[int] = mapped_column(Integer, default=1)
    price: Mapped[str] = mapped_column(Numeric(14, 4), nullable=False, default="0")
    trigger_price: Mapped[str] = mapped_column(Numeric(14, 4), nullable=False, default="0")
    status: Mapped[str] = mapped_column(
        String(25), nullable=False, index=True, default="PENDING_VALIDATION"
    )
    broker_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="SYSTEM")
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        Index("ix_orders_created", "created_at"),
        Index("ix_orders_symbol_status", "symbol", "status"),
    )


class TradeModel(Base):
    __tablename__ = "trades"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(String(32), nullable=True)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    lot_size: Mapped[int] = mapped_column(Integer, default=1)
    price: Mapped[str] = mapped_column(Numeric(14, 4), nullable=False)
    fees: Mapped[str] = mapped_column(Numeric(14, 4), default="0")
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (Index("ix_trades_executed", "executed_at"),)


class PositionModel(Base):
    __tablename__ = "positions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    instrument_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    net_quantity: Mapped[int] = mapped_column(Integer, default=0)
    average_price: Mapped[str] = mapped_column(Numeric(14, 4), default="0")
    realised_pnl: Mapped[str] = mapped_column(Numeric(14, 4), default="0")
    unrealised_pnl: Mapped[str] = mapped_column(Numeric(14, 4), default="0")
    delta: Mapped[float] = mapped_column(Numeric(10, 6), default=0.0)
    gamma: Mapped[float] = mapped_column(Numeric(10, 6), default=0.0)
    theta: Mapped[float] = mapped_column(Numeric(10, 6), default=0.0)
    vega: Mapped[float] = mapped_column(Numeric(10, 6), default=0.0)
    rho: Mapped[float] = mapped_column(Numeric(10, 6), default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class InstrumentModel(Base):
    __tablename__ = "instruments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    instrument_type: Mapped[str] = mapped_column(String(15), nullable=False)
    lot_size: Mapped[int] = mapped_column(Integer, default=1)
    tick_size: Mapped[str] = mapped_column(Numeric(10, 4), default="0.05")
    option_type: Mapped[str | None] = mapped_column(String(2), nullable=True)
    strike_price: Mapped[str | None] = mapped_column(Numeric(14, 4), nullable=True)
    expiry: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_instruments_symbol_exchange", "symbol", "exchange"),
    )
