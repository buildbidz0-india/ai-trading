"""Command handlers — write-side use cases.

Each handler encapsulates a single business operation that mutates state.
Handlers depend only on port interfaces, never on concrete adapters.
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.domain.entities import Order, Position
from app.domain.enums import Exchange, OrderSide, OrderStatus, OrderType, ProductType
from app.domain.events import OrderCancelledEvent, OrderPlacedEvent, OrderRejectedEvent
from app.domain.exceptions import OrderNotFoundError
from app.domain.services.guardrails import OrderGuardrails
from app.domain.services.risk_engine import RiskEngine, RiskVerdict
from app.domain.value_objects import Money, Quantity, Symbol
from app.ports.outbound import (
    BrokerPort,
    CachePort,
    EventBusPort,
    OrderRepository,
    PositionRepository,
)

logger = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
#  Place Order
# ═══════════════════════════════════════════════════════════════
@dataclass
class PlaceOrderCommand:
    """Input for placing a new order."""

    symbol: str
    exchange: str
    side: str
    order_type: str
    product_type: str
    quantity: int
    price: str
    trigger_price: str = "0"
    source: str = "MANUAL"


class PlaceOrderHandler:
    """Validates, risk-checks, and submits an order."""

    def __init__(
        self,
        order_repo: OrderRepository,
        position_repo: PositionRepository,
        broker: BrokerPort,
        cache: CachePort,
        event_bus: EventBusPort,
        risk_engine: RiskEngine,
        guardrails: OrderGuardrails,
        paper_mode: bool = True,
    ) -> None:
        self._order_repo = order_repo
        self._position_repo = position_repo
        self._broker = broker
        self._cache = cache
        self._event_bus = event_bus
        self._risk_engine = risk_engine
        self._guardrails = guardrails
        self._paper_mode = paper_mode

    @staticmethod
    def _compute_drawdown(open_positions: list) -> float:
        """Compute account drawdown % from open positions.

        Drawdown = abs(total_unrealised_loss) / total_invested_capital * 100.
        Returns 0.0 when there are no positions or no losses.
        """
        if not open_positions:
            return 0.0

        total_pnl = 0.0
        total_capital = 0.0

        for pos in open_positions:
            qty = float(pos.quantity.value) if hasattr(pos.quantity, "value") else float(pos.quantity)
            avg_price = float(pos.average_price.amount) if hasattr(pos.average_price, "amount") else float(pos.average_price)
            market_price = float(pos.market_price.amount) if hasattr(pos.market_price, "amount") else float(getattr(pos, "market_price", avg_price))

            invested = qty * avg_price
            total_capital += invested
            total_pnl += (market_price - avg_price) * qty

        if total_capital <= 0:
            return 0.0

        # Drawdown is the loss expressed as a positive percentage
        if total_pnl < 0:
            return abs(total_pnl) / total_capital * 100.0
        return 0.0

    async def handle(self, cmd: PlaceOrderCommand) -> Order:
        log = logger.bind(symbol=cmd.symbol, side=cmd.side, source=cmd.source)
        log.info("place_order_started")

        # 1. Build domain entity
        order = Order(
            symbol=Symbol(cmd.symbol),
            exchange=Exchange(cmd.exchange),
            side=OrderSide(cmd.side),
            order_type=OrderType(cmd.order_type),
            product_type=ProductType(cmd.product_type),
            quantity=Quantity(cmd.quantity, lot_size=1),
            price=Money.from_str(cmd.price),
            trigger_price=Money.from_str(cmd.trigger_price),
            source=cmd.source,
        )

        # 2. Guardrail sanity checks
        guardrail_result = self._guardrails.check(order)
        if not guardrail_result.passed:
            order.reject("; ".join(guardrail_result.violations))
            await self._order_repo.save(order)
            await self._event_bus.publish(
                OrderRejectedEvent(order_id=order.id, reason=order.rejection_reason or "")
            )
            log.warning("order_rejected_guardrails", violations=guardrail_result.violations)
            return order

        # 3. Risk engine evaluation
        open_positions = await self._position_repo.list_open()
        one_minute_ago = datetime.now(timezone.utc) - timedelta(minutes=1)
        recent_count = await self._order_repo.count_since(one_minute_ago)

        # Compute real account drawdown from open positions
        account_drawdown_pct = self._compute_drawdown(open_positions)

        verdict: RiskVerdict = self._risk_engine.evaluate_order(
            order=order,
            open_positions=open_positions,
            recent_order_count=recent_count,
            account_drawdown_pct=account_drawdown_pct,
        )

        if not verdict.accepted:
            order.reject(verdict.reason)
            await self._order_repo.save(order)
            await self._event_bus.publish(
                OrderRejectedEvent(order_id=order.id, reason=verdict.reason)
            )
            log.warning("order_rejected_risk", reason=verdict.reason)
            return order

        # 4. Mark validated
        order.validate()

        # 5. Submit to broker (or paper-trade) with transaction safety
        if self._paper_mode:
            broker_id = f"PAPER-{order.id[:8]}"
            log.info("paper_trade_submitted", broker_order_id=broker_id)
        else:
            broker_id = await self._broker.place_order(order)

        order.submit(broker_id)

        # Persist the order — if this fails, attempt to cancel the broker order
        # to avoid an orphaned position at the broker with no local record.
        try:
            await self._order_repo.save(order)
        except Exception as db_exc:
            log.error(
                "order_db_save_failed",
                broker_id=broker_id,
                error=str(db_exc),
            )
            if not self._paper_mode:
                try:
                    await self._broker.cancel_order(broker_id)
                    log.warning("orphaned_broker_order_cancelled", broker_id=broker_id)
                except Exception as cancel_exc:
                    log.critical(
                        "orphaned_broker_order_cancel_failed",
                        broker_id=broker_id,
                        cancel_error=str(cancel_exc),
                    )
            raise

        # 6. Publish domain event
        await self._event_bus.publish(
            OrderPlacedEvent(
                order_id=order.id,
                symbol=str(order.symbol),
                side=order.side.value,
                quantity=order.quantity.value,
                price=str(order.price.amount),
            )
        )

        log.info("place_order_completed", order_id=order.id, broker_id=broker_id)
        return order


# ═══════════════════════════════════════════════════════════════
#  Cancel Order
# ═══════════════════════════════════════════════════════════════
@dataclass
class CancelOrderCommand:
    order_id: str


class CancelOrderHandler:
    """Cancel an open order."""

    def __init__(
        self,
        order_repo: OrderRepository,
        broker: BrokerPort,
        event_bus: EventBusPort,
        paper_mode: bool = True,
    ) -> None:
        self._order_repo = order_repo
        self._broker = broker
        self._event_bus = event_bus
        self._paper_mode = paper_mode

    async def handle(self, cmd: CancelOrderCommand) -> Order:
        log = logger.bind(order_id=cmd.order_id)
        log.info("cancel_order_started")

        order = await self._order_repo.get_by_id(cmd.order_id)
        if order is None:
            raise OrderNotFoundError(cmd.order_id)

        if not self._paper_mode and order.broker_order_id:
            await self._broker.cancel_order(order.broker_order_id)

        order.cancel()
        await self._order_repo.update(order)

        await self._event_bus.publish(OrderCancelledEvent(order_id=order.id))
        log.info("cancel_order_completed")
        return order


# ═══════════════════════════════════════════════════════════════
#  Sync Positions
# ═══════════════════════════════════════════════════════════════
@dataclass
class SyncPositionsCommand:
    """Trigger position reconciliation with broker."""

    pass


class SyncPositionsHandler:
    """Pull positions from broker and reconcile with local state."""

    def __init__(
        self,
        position_repo: PositionRepository,
        broker: BrokerPort,
    ) -> None:
        self._position_repo = position_repo
        self._broker = broker

    async def handle(self, _cmd: SyncPositionsCommand) -> list[Position]:
        log = logger.bind(action="sync_positions")
        log.info("sync_positions_started")

        broker_positions = await self._broker.get_positions()
        synced: list[Position] = []

        for bp in broker_positions:
            instrument_id = str(bp.get("instrument_id", ""))
            existing = await self._position_repo.get_by_instrument(instrument_id)

            if existing:
                existing.net_quantity = int(bp.get("net_quantity", 0))
                await self._position_repo.update(existing)
                synced.append(existing)
            else:
                pos = Position(
                    instrument_id=instrument_id,
                    symbol=Symbol(str(bp.get("symbol", "UNKNOWN"))),
                    net_quantity=int(bp.get("net_quantity", 0)),
                )
                await self._position_repo.save(pos)
                synced.append(pos)

        log.info("sync_positions_completed", count=len(synced))
        return synced
