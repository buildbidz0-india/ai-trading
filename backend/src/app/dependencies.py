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

from app.adapters.outbound.broker import (
    DhanBrokerAdapter,
    PaperBrokerAdapter,
    ShoonyaBrokerAdapter,
    ZerodhaBrokerAdapter,
)
from app.adapters.outbound.cache import RedisCacheAdapter
from app.adapters.outbound.event_bus import InProcessEventBus
from app.adapters.outbound.llm import ResilientLLMAdapter, build_provider_configs
from app.adapters.outbound.persistence.database import create_session_factory
from app.adapters.outbound.persistence.repositories import (
    SQLAlchemyInstrumentRepository,
    SQLAlchemyOrderRepository,
    SQLAlchemyPositionRepository,
    SQLAlchemyOrderRepository,
    SQLAlchemyPositionRepository,
    SQLAlchemyTradeRepository,
    SQLAlchemyUserRepository,
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
from app.shared.providers.types import RoutingStrategy
from app.shared.security import decode_token


# ── Settings ─────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_cached_settings() -> Settings:
    return get_settings()


# ── Singletons ───────────────────────────────────────────────
_session_factory: async_sessionmaker[AsyncSession] | None = None
_cache: RedisCacheAdapter | None = None
_event_bus: InProcessEventBus | None = None
_broker: PaperBrokerAdapter | DhanBrokerAdapter | ZerodhaBrokerAdapter | ShoonyaBrokerAdapter | None = None
_llm: ResilientLLMAdapter | None = None

import asyncio

_init_lock = asyncio.Lock()


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


async def get_broker(settings: Settings | None = None):  # type: ignore[no-untyped-def]
    """Factory that selects broker adapter based on BROKER_PROVIDER config.

    Uses asyncio.Lock to prevent double-initialization under concurrent access.
    """
    global _broker
    if _broker is not None:
        return _broker
    async with _init_lock:
        if _broker is not None:
            return _broker  # another coroutine won the race
        s = settings or get_cached_settings()
        provider = s.broker_provider.lower()
        if provider == "dhan":
            _broker = DhanBrokerAdapter(
                client_id=s.dhan_client_id,
                access_token=s.dhan_access_token,
            )
        elif provider == "zerodha":
            _broker = ZerodhaBrokerAdapter(
                api_key=s.zerodha_api_key,
                api_secret=s.zerodha_api_secret,
            )
        elif provider == "shoonya":
            _broker = ShoonyaBrokerAdapter(
                user_id=s.shoonya_user_id,
                password=s.shoonya_password,
                api_key=s.shoonya_api_key,
            )
        else:
            _broker = PaperBrokerAdapter()
    return _broker


def get_llm(settings: Settings | None = None) -> ResilientLLMAdapter:
    """Create or return the singleton resilient LLM adapter.

    Builds ProviderConfig objects from settings, then constructs
    the gateway-backed adapter with rotation, failover, and health.
    """
    global _llm
    if _llm is None:
        s = settings or get_cached_settings()

        # Parse routing strategy
        strategy_map = {v.value: v for v in RoutingStrategy}
        strategy = strategy_map.get(s.llm_routing_strategy, RoutingStrategy.PRIORITY_FAILOVER)

        # Build provider configs from settings
        provider_configs = build_provider_configs(
            anthropic_api_key=s.anthropic_api_key,
            openai_api_key=s.openai_api_key,
            openai_base_url=s.openai_base_url,
            google_api_key=s.google_api_key,
            anthropic_api_keys=s.anthropic_api_keys,
            openai_api_keys=s.openai_api_keys,
            google_api_keys=s.google_api_keys,
            anthropic_model=s.anthropic_model,
            openai_model=s.openai_model,
            google_model=s.google_model,
            anthropic_rpm=s.anthropic_rpm,
            openai_rpm=s.openai_rpm,
            google_rpm=s.google_rpm,
            anthropic_tpm=s.anthropic_tpm,
            openai_tpm=s.openai_tpm,
            google_tpm=s.google_tpm,
            timeout_s=s.provider_timeout_seconds,
            cb_failure_threshold=s.circuit_breaker_failure_threshold,
            cb_cooldown_s=s.circuit_breaker_cooldown_seconds,
            priority_order=s.llm_provider_priority,
        )

        _llm = ResilientLLMAdapter(
            provider_configs,
            routing_strategy=strategy,
            timeout=s.provider_timeout_seconds,
            backoff_base=s.provider_backoff_base,
            backoff_max=s.provider_backoff_max,
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


async def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> SQLAlchemyUserRepository:
    return SQLAlchemyUserRepository(session)


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
    
    # Verify user exists in DB and is active
    factory = get_session_factory(settings)
    async with factory() as session:
        repo = SQLAlchemyUserRepository(session)
        user = await repo.get_by_username(payload.get("sub", ""))
        
        if not user or not user.is_active:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Return dict expected by endpoints (mostly) but include role
        # We can return the user dict from the payload with added role from DB if needed,
        # or just the payload if the token claims are trusted. 
        # But for RBAC, we want the current role from DB to support immediate revocations.
        return {
            "username": user.username,
            "role": user.role,
            "id": user.id,
            "email": user.email
        }


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
