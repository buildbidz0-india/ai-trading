"""Concrete repository implementations using SQLAlchemy.

These adapters implement the outbound port interfaces, translating between
domain entities and ORM models.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Instrument, Order, Position, Trade
from app.domain.enums import (
    Exchange,
    InstrumentType,
    OrderSide,
    OrderStatus,
    OrderType,
    ProductType,
)
from app.domain.value_objects import Greeks, Money, Quantity, Symbol
from app.ports.outbound import (
    InstrumentRepository,
    OrderRepository,
    PositionRepository,
    TradeRepository,
)

from .models import InstrumentModel, OrderModel, PositionModel, TradeModel


# ── Converters ───────────────────────────────────────────────
def _order_to_model(o: Order) -> OrderModel:
    return OrderModel(
        id=o.id,
        instrument_id=o.instrument_id,
        symbol=str(o.symbol),
        exchange=o.exchange.value,
        side=o.side.value,
        order_type=o.order_type.value,
        product_type=o.product_type.value,
        quantity=o.quantity.value,
        lot_size=o.quantity.lot_size,
        price=str(o.price.amount),
        trigger_price=str(o.trigger_price.amount),
        status=o.status.value,
        broker_order_id=o.broker_order_id,
        idempotency_key=o.idempotency_key,
        source=o.source,
        rejection_reason=o.rejection_reason,
        created_at=o.created_at,
        updated_at=o.updated_at,
    )


def _model_to_order(m: OrderModel) -> Order:
    return Order(
        id=m.id,
        instrument_id=m.instrument_id or "",
        symbol=Symbol(m.symbol),
        exchange=Exchange(m.exchange),
        side=OrderSide(m.side),
        order_type=OrderType(m.order_type),
        product_type=ProductType(m.product_type),
        quantity=Quantity(m.quantity, lot_size=m.lot_size),
        price=Money(Decimal(str(m.price))),
        trigger_price=Money(Decimal(str(m.trigger_price))),
        status=OrderStatus(m.status),
        broker_order_id=m.broker_order_id,
        idempotency_key=m.idempotency_key,
        source=m.source,
        rejection_reason=m.rejection_reason,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _model_to_position(m: PositionModel) -> Position:
    return Position(
        id=m.id,
        instrument_id=m.instrument_id,
        symbol=Symbol(m.symbol),
        exchange=Exchange(m.exchange),
        net_quantity=m.net_quantity,
        average_price=Money(Decimal(str(m.average_price))),
        realised_pnl=Money(Decimal(str(m.realised_pnl))),
        unrealised_pnl=Money(Decimal(str(m.unrealised_pnl))),
        greeks=Greeks(
            delta=float(m.delta),
            gamma=float(m.gamma),
            theta=float(m.theta),
            vega=float(m.vega),
            rho=float(m.rho),
        ),
        updated_at=m.updated_at,
    )


# ═══════════════════════════════════════════════════════════════
#  SQLAlchemy Order Repository
# ═══════════════════════════════════════════════════════════════
class SQLAlchemyOrderRepository(OrderRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, order: Order) -> None:
        model = _order_to_model(order)
        self._session.add(model)
        await self._session.flush()

    async def get_by_id(self, order_id: str) -> Order | None:
        result = await self._session.get(OrderModel, order_id)
        return _model_to_order(result) if result else None

    async def list_by_status(
        self, status: OrderStatus, *, limit: int = 100
    ) -> list[Order]:
        stmt = (
            select(OrderModel)
            .where(OrderModel.status == status.value)
            .order_by(OrderModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_model_to_order(r) for r in result.scalars()]

    async def list_recent(
        self, *, since: datetime | None = None, limit: int = 100
    ) -> list[Order]:
        stmt = select(OrderModel).order_by(OrderModel.created_at.desc()).limit(limit)
        if since:
            stmt = stmt.where(OrderModel.created_at >= since)
        result = await self._session.execute(stmt)
        return [_model_to_order(r) for r in result.scalars()]

    async def count_since(self, since: datetime) -> int:
        stmt = select(func.count()).select_from(OrderModel).where(
            OrderModel.created_at >= since
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def update(self, order: Order) -> None:
        stmt = (
            update(OrderModel)
            .where(OrderModel.id == order.id)
            .values(
                status=order.status.value,
                broker_order_id=order.broker_order_id,
                rejection_reason=order.rejection_reason,
                updated_at=order.updated_at,
            )
        )
        await self._session.execute(stmt)


# ═══════════════════════════════════════════════════════════════
#  SQLAlchemy Trade Repository
# ═══════════════════════════════════════════════════════════════
class SQLAlchemyTradeRepository(TradeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, trade: Trade) -> None:
        model = TradeModel(
            id=trade.id,
            order_id=trade.order_id,
            instrument_id=trade.instrument_id,
            symbol=str(trade.symbol),
            exchange=trade.exchange.value,
            side=trade.side.value,
            quantity=trade.quantity.value,
            lot_size=trade.quantity.lot_size,
            price=str(trade.price.amount),
            fees=str(trade.fees.amount),
            executed_at=trade.executed_at,
        )
        self._session.add(model)
        await self._session.flush()

    async def get_by_id(self, trade_id: str) -> Trade | None:
        result = await self._session.get(TradeModel, trade_id)
        if not result:
            return None
        return Trade(
            id=result.id,
            order_id=result.order_id,
            instrument_id=result.instrument_id or "",
            symbol=Symbol(result.symbol),
            exchange=Exchange(result.exchange),
            side=OrderSide(result.side),
            quantity=Quantity(result.quantity, lot_size=result.lot_size),
            price=Money(Decimal(str(result.price))),
            fees=Money(Decimal(str(result.fees))),
            executed_at=result.executed_at,
        )

    async def list_by_order(self, order_id: str) -> list[Trade]:
        stmt = select(TradeModel).where(TradeModel.order_id == order_id)
        result = await self._session.execute(stmt)
        return [
            Trade(
                id=r.id,
                order_id=r.order_id,
                symbol=Symbol(r.symbol),
                exchange=Exchange(r.exchange),
                side=OrderSide(r.side),
                quantity=Quantity(r.quantity, lot_size=r.lot_size),
                price=Money(Decimal(str(r.price))),
                fees=Money(Decimal(str(r.fees))),
                executed_at=r.executed_at,
            )
            for r in result.scalars()
        ]

    async def list_recent(
        self, *, since: datetime | None = None, limit: int = 100
    ) -> list[Trade]:
        stmt = (
            select(TradeModel).order_by(TradeModel.executed_at.desc()).limit(limit)
        )
        if since:
            stmt = stmt.where(TradeModel.executed_at >= since)
        result = await self._session.execute(stmt)
        return [
            Trade(
                id=r.id,
                order_id=r.order_id,
                symbol=Symbol(r.symbol),
                exchange=Exchange(r.exchange),
                side=OrderSide(r.side),
                quantity=Quantity(r.quantity, lot_size=r.lot_size),
                price=Money(Decimal(str(r.price))),
                fees=Money(Decimal(str(r.fees))),
                executed_at=r.executed_at,
            )
            for r in result.scalars()
        ]


# ═══════════════════════════════════════════════════════════════
#  SQLAlchemy Position Repository
# ═══════════════════════════════════════════════════════════════
class SQLAlchemyPositionRepository(PositionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, position: Position) -> None:
        model = PositionModel(
            id=position.id,
            instrument_id=position.instrument_id,
            symbol=str(position.symbol),
            exchange=position.exchange.value,
            net_quantity=position.net_quantity,
            average_price=str(position.average_price.amount),
            realised_pnl=str(position.realised_pnl.amount),
            unrealised_pnl=str(position.unrealised_pnl.amount),
            delta=position.greeks.delta,
            gamma=position.greeks.gamma,
            theta=position.greeks.theta,
            vega=position.greeks.vega,
            rho=position.greeks.rho,
            updated_at=position.updated_at,
        )
        self._session.add(model)
        await self._session.flush()

    async def get_by_instrument(self, instrument_id: str) -> Position | None:
        stmt = select(PositionModel).where(
            PositionModel.instrument_id == instrument_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _model_to_position(model) if model else None

    async def list_open(self) -> list[Position]:
        stmt = select(PositionModel).where(PositionModel.net_quantity != 0)
        result = await self._session.execute(stmt)
        return [_model_to_position(r) for r in result.scalars()]

    async def list_all(self) -> list[Position]:
        stmt = select(PositionModel)
        result = await self._session.execute(stmt)
        return [_model_to_position(r) for r in result.scalars()]

    async def update(self, position: Position) -> None:
        stmt = (
            update(PositionModel)
            .where(PositionModel.id == position.id)
            .values(
                net_quantity=position.net_quantity,
                average_price=str(position.average_price.amount),
                realised_pnl=str(position.realised_pnl.amount),
                unrealised_pnl=str(position.unrealised_pnl.amount),
                delta=position.greeks.delta,
                gamma=position.greeks.gamma,
                theta=position.greeks.theta,
                vega=position.greeks.vega,
                rho=position.greeks.rho,
            )
        )
        await self._session.execute(stmt)


# ═══════════════════════════════════════════════════════════════
#  SQLAlchemy Instrument Repository
# ═══════════════════════════════════════════════════════════════
class SQLAlchemyInstrumentRepository(InstrumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, instrument_id: str) -> Instrument | None:
        result = await self._session.get(InstrumentModel, instrument_id)
        return self._to_entity(result) if result else None

    async def get_by_symbol(
        self, symbol: Symbol, *, exchange: str | None = None
    ) -> list[Instrument]:
        stmt = select(InstrumentModel).where(InstrumentModel.symbol == str(symbol))
        if exchange:
            stmt = stmt.where(InstrumentModel.exchange == exchange)
        result = await self._session.execute(stmt)
        return [self._to_entity(r) for r in result.scalars()]

    async def save(self, instrument: Instrument) -> None:
        model = InstrumentModel(
            id=instrument.id,
            symbol=str(instrument.symbol),
            exchange=instrument.exchange.value,
            instrument_type=instrument.instrument_type.value,
            lot_size=instrument.lot_size,
            tick_size=str(instrument.tick_size),
            option_type=instrument.option_type.value if instrument.option_type else None,
            strike_price=(
                str(instrument.strike_price.value) if instrument.strike_price else None
            ),
            expiry=instrument.expiry.date if instrument.expiry else None,
        )
        self._session.add(model)
        await self._session.flush()

    async def search(self, query: str, *, limit: int = 20) -> list[Instrument]:
        # Escape SQL LIKE wildcards in user input
        safe_query = query.replace("%", r"\%").replace("_", r"\_")
        stmt = (
            select(InstrumentModel)
            .where(InstrumentModel.symbol.ilike(f"%{safe_query}%"))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(r) for r in result.scalars()]

    @staticmethod
    def _to_entity(m: InstrumentModel) -> Instrument:
        from app.domain.value_objects import Expiry, StrikePrice

        return Instrument(
            id=m.id,
            symbol=Symbol(m.symbol),
            exchange=Exchange(m.exchange),
            instrument_type=InstrumentType(m.instrument_type),
            lot_size=m.lot_size,
            tick_size=Decimal(str(m.tick_size)),
            option_type=None,  # simplified
            strike_price=(
                StrikePrice(Decimal(str(m.strike_price))) if m.strike_price else None
            ),
            expiry=Expiry(m.expiry.date()) if m.expiry else None,
        )
