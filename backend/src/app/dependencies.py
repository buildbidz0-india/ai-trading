"""Dependency injection container — wires adapters to ports.

FastAPI's ``Depends()`` system uses these factories to inject the
correct adapter implementations into route handlers.
"""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Any, AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.adapters.outbound.broker import PaperBrokerAdapter
from app.adapters.outbound.cache import RedisCacheAdapter
from app.adapters.outbound.event_bus import InProcessEventBus
from app.adapters.outbound.llm import MultiProviderLLMAdapter
from app.adapters.outbound.persistence.database import create_session_factory
from app.adapters.outbound.persistence.repositories import (
    SQLAlchemyInstrumentRepository,
    SQLAlchemyOrderRepository,
    SQLAlchemyPositionRepository,
    SQLAlchemyTradeRepository,
)
from app.application.commands import (
    CancelOrderHandler,
    PlaceOrderHandler,
    SyncPositionsHandler,
)
from app.application.queries import (
    GetOptionChainHandler,
    GetOrdersHandler,
    GetPositionsHandler,
    GetTradeHistoryHandler,
    SearchInstrumentsHandler,
)
from app.application.services import AIOrchestrationService
from app.config import Settings, get_settings
from app.domain.services.guardrails import OrderGuardrails
from app.domain.services.risk_engine import RiskEngine, RiskLimits
from app.domain.value_objects import Money
from app.shared.security import decode_token


# ── Settings ─────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_cached_settings() -> Settings:
    return get_settings()


# ── Singletons ───────────────────────────────────────────────
_session_factory: async_sessionmaker[AsyncSession] | None = None
_cache: RedisCacheAdapter | None = None
_event_bus: InProcessEventBus | None = None
_broker: PaperBrokerAdapter | None = None
_llm: MultiProviderLLMAdapter | None = None


def get_session_factory(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        s = settings or get_cached_settings()
        _session_factory = create_session_factory(s)
    return _session_factory


def get_cache(settings: Settings | None = None) -> RedisCacheAdapter:
    global _cache
    if _cache is None:
        s = settings or get_cached_settings()
        _cache = RedisCacheAdapter(s.redis_url, s.redis_max_connections)
    return _cache


def get_event_bus() -> InProcessEventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = InProcessEventBus()
    return _event_bus


def get_broker() -> PaperBrokerAdapter:
    global _broker
    if _broker is None:
        _broker = PaperBrokerAdapter()
    return _broker


def get_llm(settings: Settings | None = None) -> MultiProviderLLMAdapter:
    global _llm
    if _llm is None:
        s = settings or get_cached_settings()
        _llm = MultiProviderLLMAdapter(
            anthropic_api_key=s.anthropic_api_key,
            openai_api_key=s.openai_api_key,
            google_api_key=s.google_api_key,
        )
    return _llm


# ── DB session dependency ────────────────────────────────────
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Auth dependency ──────────────────────────────────────────
async def get_current_user(
    authorization: str = Header(None, alias="Authorization"),
) -> dict[str, Any]:
    """Extract and validate JWT from Authorization header."""
    settings = get_cached_settings()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token, settings.jwt_secret_key, settings.jwt_algorithm)
    return payload


# ── Use-case handler factories ───────────────────────────────
def get_place_order_handler(
    session: AsyncSession = Depends(get_db_session),
) -> PlaceOrderHandler:
    settings = get_cached_settings()
    return PlaceOrderHandler(
        order_repo=SQLAlchemyOrderRepository(session),
        position_repo=SQLAlchemyPositionRepository(session),
        broker=get_broker(),
        cache=get_cache(),
        event_bus=get_event_bus(),
        risk_engine=RiskEngine(
            RiskLimits(
                max_order_value=Money(Decimal(str(settings.max_order_value_inr))),
                max_position_delta=settings.max_position_delta,
                max_orders_per_minute=settings.max_orders_per_minute,
                kill_switch_drawdown_pct=settings.kill_switch_drawdown_pct,
            )
        ),
        guardrails=OrderGuardrails(),
        paper_mode=settings.paper_trading_mode,
    )


def get_cancel_order_handler(
    session: AsyncSession = Depends(get_db_session),
) -> CancelOrderHandler:
    settings = get_cached_settings()
    return CancelOrderHandler(
        order_repo=SQLAlchemyOrderRepository(session),
        broker=get_broker(),
        event_bus=get_event_bus(),
        paper_mode=settings.paper_trading_mode,
    )


def get_sync_positions_handler(
    session: AsyncSession = Depends(get_db_session),
) -> SyncPositionsHandler:
    return SyncPositionsHandler(
        position_repo=SQLAlchemyPositionRepository(session),
        broker=get_broker(),
    )


def get_positions_handler(
    session: AsyncSession = Depends(get_db_session),
) -> GetPositionsHandler:
    return GetPositionsHandler(SQLAlchemyPositionRepository(session))


def get_orders_handler(
    session: AsyncSession = Depends(get_db_session),
) -> GetOrdersHandler:
    return GetOrdersHandler(SQLAlchemyOrderRepository(session))


def get_trade_history_handler(
    session: AsyncSession = Depends(get_db_session),
) -> GetTradeHistoryHandler:
    return GetTradeHistoryHandler(SQLAlchemyTradeRepository(session))


def get_option_chain_handler() -> GetOptionChainHandler:
    return GetOptionChainHandler(get_cache())


def get_instruments_handler(
    session: AsyncSession = Depends(get_db_session),
) -> SearchInstrumentsHandler:
    return SearchInstrumentsHandler(SQLAlchemyInstrumentRepository(session))


def get_ai_orchestration_service() -> AIOrchestrationService:
    return AIOrchestrationService(
        llm=get_llm(),
        cache=get_cache(),
        event_bus=get_event_bus(),
    )
