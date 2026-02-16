"""Query handlers — read-side use cases.

Query handlers are intentionally simple: they fetch data from repositories
or caches and return DTOs.  No mutation of domain state happens here.
"""

from __future__ import annotations

import structlog
from dataclasses import dataclass
from datetime import datetime

from app.domain.entities import Order, Position, Trade
from app.domain.enums import OrderStatus
from app.ports.outbound import (
    CachePort,
    InstrumentRepository,
    OrderRepository,
    PositionRepository,
    TradeRepository,
)

logger = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
#  Get Positions
# ═══════════════════════════════════════════════════════════════
@dataclass
class GetPositionsQuery:
    open_only: bool = True


class GetPositionsHandler:
    def __init__(self, position_repo: PositionRepository) -> None:
        self._repo = position_repo

    async def handle(self, query: GetPositionsQuery) -> list[Position]:
        logger.debug("get_positions", open_only=query.open_only)
        if query.open_only:
            return await self._repo.list_open()
        return await self._repo.list_all()


# ═══════════════════════════════════════════════════════════════
#  Get Orders
# ═══════════════════════════════════════════════════════════════
@dataclass
class GetOrdersQuery:
    status: OrderStatus | None = None
    since: datetime | None = None
    limit: int = 100


class GetOrdersHandler:
    def __init__(self, order_repo: OrderRepository) -> None:
        self._repo = order_repo

    async def handle(self, query: GetOrdersQuery) -> list[Order]:
        logger.debug("get_orders", status=query.status, limit=query.limit)
        if query.status:
            return await self._repo.list_by_status(query.status, limit=query.limit)
        return await self._repo.list_recent(since=query.since, limit=query.limit)


# ═══════════════════════════════════════════════════════════════
#  Get Trade History
# ═══════════════════════════════════════════════════════════════
@dataclass
class GetTradeHistoryQuery:
    since: datetime | None = None
    limit: int = 100


class GetTradeHistoryHandler:
    def __init__(self, trade_repo: TradeRepository) -> None:
        self._repo = trade_repo

    async def handle(self, query: GetTradeHistoryQuery) -> list[Trade]:
        logger.debug("get_trade_history", limit=query.limit)
        return await self._repo.list_recent(since=query.since, limit=query.limit)


# ═══════════════════════════════════════════════════════════════
#  Get Option Chain (from cache)
# ═══════════════════════════════════════════════════════════════
@dataclass
class GetOptionChainQuery:
    symbol: str
    expiry: str | None = None


class GetOptionChainHandler:
    def __init__(self, cache: CachePort) -> None:
        self._cache = cache

    async def handle(self, query: GetOptionChainQuery) -> dict | None:  # type: ignore[type-arg]
        logger.debug("get_option_chain", symbol=query.symbol)
        key = f"option_chain:{query.symbol}"
        if query.expiry:
            key += f":{query.expiry}"
        raw = await self._cache.get(key)
        if raw:
            import orjson

            return orjson.loads(raw)  # type: ignore[no-any-return]
        return None


# ═══════════════════════════════════════════════════════════════
#  Search Instruments
# ═══════════════════════════════════════════════════════════════
@dataclass
class SearchInstrumentsQuery:
    query: str
    limit: int = 20


class SearchInstrumentsHandler:
    def __init__(self, instrument_repo: InstrumentRepository) -> None:
        self._repo = instrument_repo

    async def handle(self, query: SearchInstrumentsQuery):  # type: ignore[no-untyped-def]
        logger.debug("search_instruments", q=query.query)
        return await self._repo.search(query.query, limit=query.limit)
