"""Health, Auth, Orders, Positions, Trades, Instruments, AI — REST routers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from app.adapters.outbound.persistence.models import UserModel
from app.adapters.outbound.persistence.repositories import SQLAlchemyUserRepository

from app.application.commands import (
    CancelOrderCommand,
    CancelOrderHandler,
    PlaceOrderCommand,
    PlaceOrderHandler,
)
from app.application.dtos import (
    AIAnalysisRequest,
    AIAnalysisResponse,
    AgentOutput,
    CancelOrderRequest,
    ErrorResponse,
    HealthResponse,
    OrderResponse,
    PlaceOrderRequest,
    PositionResponse,
    TokenRequest,
    TokenResponse,
    TradeResponse,
)
from app.application.queries import (
    GetOrdersHandler,
    GetOrdersQuery,
    GetPositionsHandler,
    GetPositionsQuery,
    GetTradeHistoryHandler,
    GetTradeHistoryQuery,
)
from app.application.services import AIOrchestrationService
from app.config import Settings
from app.dependencies import (
    get_ai_orchestration_service,
    get_broker,
    get_cached_settings,
    get_cancel_order_handler,
    get_current_user,
    get_orders_handler,
    get_place_order_handler,
    get_positions_handler,
    get_trade_history_handler,
    get_user_repository,
)
from app.shared.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.shared.security.rbac import require_role


# ═══════════════════════════════════════════════════════════════
#  Health
# ═══════════════════════════════════════════════════════════════
health_router = APIRouter(tags=["Health"])


@health_router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_cached_settings()
    from starlette.responses import JSONResponse

    # ── Check Redis ──────────────────────────────────────────
    redis_status = "connected"
    redis_error = None
    try:
        from app.dependencies import get_cache
        cache = get_cache()
        if not await cache.health_check():
            redis_status = "disconnected"
            redis_error = "Ping failed"
    except Exception as e:
        redis_status = "disconnected"
        redis_error = str(e)

    # ── Check Database ───────────────────────────────────────
    db_status = "connected"
    db_error = None
    try:
        from app.dependencies import get_session_factory
        from sqlalchemy import text
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "disconnected"
        db_error = str(e)

    # Database is critical for 'ok' status, Redis is optional for MVP
    overall = "ok" if db_status == "connected" else "degraded"

    resp_data = {
        "status": overall,
        "version": "0.1.0",
        "environment": settings.app_env.value,
        "services": {
            "database": db_status,
            "redis": redis_status,
            "broker": f"{settings.broker_provider} (paper_mode={settings.paper_trading_mode})",
        }
    }
    
    if db_error:
        resp_data["services"]["database_error"] = db_error
    if redis_error:
        resp_data["services"]["redis_error"] = redis_error

    status_code = 200 if overall == "ok" else 503
    return JSONResponse(content=resp_data, status_code=status_code)


@health_router.get("/metrics")
async def prometheus_metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# ═══════════════════════════════════════════════════════════════
#  Auth
# ═══════════════════════════════════════════════════════════════
auth_router = APIRouter(prefix="/auth", tags=["Authentication"]) # Removed duplicate definition


@auth_router.post("/register", status_code=201)
async def register_user(
    body: TokenRequest,
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> dict[str, str]:
    """Register a new user (admin or trader). For MVP, open registration."""
    if await user_repo.username_exists(body.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
        )
    
    # Create user
    new_user = UserModel(
        id=str(uuid.uuid4()), # Added id field
        username=body.username,
        email=f"{body.username}@example.com",  # Placeholder email
        password_hash=hash_password(body.password),
        role="trader",  # Default role
        is_active=True,
    )
    await user_repo.create(new_user)
    return {"message": "User created successfully"}


@auth_router.post("/token", response_model=TokenResponse)
async def create_token(
    body: TokenRequest,
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> TokenResponse:
    """Login with username and password."""
    settings = get_cached_settings()
    
    user = await user_repo.get_by_username(body.username)
    if not user or not verify_password(body.password, user.password_hash):
        from app.domain.exceptions import AuthenticationError
        raise AuthenticationError("Invalid credentials")

    if not user.is_active:
        raise AuthenticationError("User is inactive")

    token_data = {"sub": user.username, "role": user.role, "id": user.id}
    access = create_access_token(
        token_data,
        settings.jwt_secret_key,
        settings.jwt_algorithm,
        settings.jwt_access_token_expire_minutes,
    )
    refresh = create_refresh_token(
        token_data,
        settings.jwt_secret_key,
        settings.jwt_algorithm,
        settings.jwt_refresh_token_expire_days,
    )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(
    refresh_token: str,
    user_repo: SQLAlchemyUserRepository = Depends(get_user_repository),
) -> TokenResponse:
    """Exchange refresh token for new access token."""
    settings = get_cached_settings()
    
    try:
        payload = decode_token(refresh_token, settings.jwt_secret_key, settings.jwt_algorithm)
        if payload.get("type") != "refresh":
             raise HTTPException(status_code=401, detail="Invalid token type")
        
        username = payload.get("sub")
        user = await user_repo.get_by_username(username)
        if not user or not user.is_active:
             raise HTTPException(status_code=401, detail="User not found or inactive")
             
        # Issue new access token
        token_data = {"sub": user.username, "role": user.role, "id": user.id}
        new_access = create_access_token(
            token_data,
            settings.jwt_secret_key,
            settings.jwt_algorithm,
            settings.jwt_access_token_expire_minutes,
        )
        # Optionally rotate refresh token here too
        
        return TokenResponse(
            access_token=new_access,
            refresh_token=refresh_token, # Keep existing refresh token until expiry
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid refresh token: {str(e)}")


# ═══════════════════════════════════════════════════════════════
#  Orders
# ═══════════════════════════════════════════════════════════════
orders_router = APIRouter(prefix="/orders", tags=["Orders"])


@orders_router.post(
    "",
    response_model=OrderResponse,
    status_code=201,
    responses={403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def place_order(
    body: PlaceOrderRequest,
    handler: PlaceOrderHandler = Depends(get_place_order_handler),
    _user: dict = Depends(get_current_user),
) -> OrderResponse:
    cmd = PlaceOrderCommand(
        symbol=body.symbol,
        exchange=body.exchange,
        side=body.side,
        order_type=body.order_type,
        product_type=body.product_type,
        quantity=body.quantity,
        price=str(body.price),
        trigger_price=str(body.trigger_price),
        source=body.source,
    )
    order = await handler.handle(cmd)
    return OrderResponse(
        id=order.id,
        symbol=str(order.symbol),
        exchange=order.exchange.value,
        side=order.side.value,
        order_type=order.order_type.value,
        product_type=order.product_type.value,
        quantity=order.quantity.value,
        price=str(order.price.amount),
        status=order.status.value,
        broker_order_id=order.broker_order_id,
        rejection_reason=order.rejection_reason,
        source=order.source,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@orders_router.get("", response_model=list[OrderResponse])
async def list_orders(
    limit: int = 50,
    handler: GetOrdersHandler = Depends(get_orders_handler),
    _user: dict = Depends(get_current_user),
) -> list[OrderResponse]:
    orders = await handler.handle(GetOrdersQuery(limit=limit))
    return [
        OrderResponse(
            id=o.id,
            symbol=str(o.symbol),
            exchange=o.exchange.value,
            side=o.side.value,
            order_type=o.order_type.value,
            product_type=o.product_type.value,
            quantity=o.quantity.value,
            price=str(o.price.amount),
            status=o.status.value,
            broker_order_id=o.broker_order_id,
            rejection_reason=o.rejection_reason,
            source=o.source,
            created_at=o.created_at,
            updated_at=o.updated_at,
        )
        for o in orders
    ]


@orders_router.delete("/{order_id}", response_model=OrderResponse)
async def cancel_order(
    order_id: str,
    handler: CancelOrderHandler = Depends(get_cancel_order_handler),
    _user: dict = Depends(get_current_user),
) -> OrderResponse:
    order = await handler.handle(CancelOrderCommand(order_id=order_id))
    return OrderResponse(
        id=order.id,
        symbol=str(order.symbol),
        exchange=order.exchange.value,
        side=order.side.value,
        order_type=order.order_type.value,
        product_type=order.product_type.value,
        quantity=order.quantity.value,
        price=str(order.price.amount),
        status=order.status.value,
        broker_order_id=order.broker_order_id,
        rejection_reason=order.rejection_reason,
        source=order.source,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


# ═══════════════════════════════════════════════════════════════
#  Positions
# ═══════════════════════════════════════════════════════════════
positions_router = APIRouter(prefix="/positions", tags=["Positions"])


@positions_router.get("", response_model=list[PositionResponse])
async def list_positions(
    handler: GetPositionsHandler = Depends(get_positions_handler),
    _user: dict = Depends(get_current_user),
) -> list[PositionResponse]:
    positions = await handler.handle(GetPositionsQuery())
    return [
        PositionResponse(
            id=p.id,
            instrument_id=p.instrument_id,
            symbol=str(p.symbol),
            exchange=p.exchange.value,
            net_quantity=p.net_quantity,
            average_price=str(p.average_price.amount),
            realised_pnl=str(p.realised_pnl.amount),
            unrealised_pnl=str(p.unrealised_pnl.amount),
            greeks={
                "delta": p.greeks.delta,
                "gamma": p.greeks.gamma,
                "theta": p.greeks.theta,
                "vega": p.greeks.vega,
                "rho": p.greeks.rho,
            },
            updated_at=p.updated_at,
        )
        for p in positions
    ]


# ═══════════════════════════════════════════════════════════════
#  Trades
# ═══════════════════════════════════════════════════════════════
trades_router = APIRouter(prefix="/trades", tags=["Trades"])


@trades_router.get("", response_model=list[TradeResponse])
async def list_trades(
    limit: int = 50,
    handler: GetTradeHistoryHandler = Depends(get_trade_history_handler),
    _user: dict = Depends(get_current_user),
) -> list[TradeResponse]:
    trades = await handler.handle(GetTradeHistoryQuery(limit=limit))
    return [
        TradeResponse(
            id=t.id,
            order_id=t.order_id,
            symbol=str(t.symbol),
            exchange=t.exchange.value,
            side=t.side.value,
            quantity=t.quantity.value,
            price=str(t.price.amount),
            fees=str(t.fees.amount),
            executed_at=t.executed_at,
        )
        for t in trades
    ]


# ═══════════════════════════════════════════════════════════════
#  AI Analysis
# ═══════════════════════════════════════════════════════════════
ai_router = APIRouter(prefix="/ai", tags=["AI Analysis"])


@ai_router.post("/analyze", response_model=AIAnalysisResponse)
async def trigger_analysis(
    body: AIAnalysisRequest,
    _user: dict = Depends(get_current_user),
) -> AIAnalysisResponse:
    service = get_ai_orchestration_service()
    result = await service.analyze(body.symbol, body.context)
    return AIAnalysisResponse(
        symbol=result.symbol,
        agents=[
            AgentOutput(
                agent_role=r.role.value,
                provider=r.provider.value,
                confidence=r.confidence,
                latency_ms=r.latency_ms,
                summary=str(r.output),
                raw_output=r.output if not r.error else None,
            )
            for r in result.results
        ],
        recommended_action=result.recommended_action,
        overall_confidence=result.overall_confidence,
        timestamp=datetime.now(timezone.utc),
    )


# ═══════════════════════════════════════════════════════════════
#  Provider Health (Admin)
# ═══════════════════════════════════════════════════════════════
from app.dependencies import get_llm  # noqa: E402
from app.adapters.outbound.llm import ResilientLLMAdapter  # noqa: E402

providers_router = APIRouter(prefix="/providers", tags=["Provider Health"])


@providers_router.get("/health")
async def provider_health(
    _user: dict = Depends(get_current_user),
) -> list[dict]:
    """Get health snapshots for all configured API providers."""
    llm = get_llm()
    healths = llm.gateway.get_all_health()
    return [
        {
            "provider_id": h.provider_id,
            "status": h.status.value,
            "total_requests": h.total_requests,
            "total_successes": h.total_successes,
            "total_failures": h.total_failures,
            "consecutive_failures": h.consecutive_failures,
            "success_rate": h.success_rate,
            "latency_p50_ms": h.latency_p50_ms,
            "latency_p95_ms": h.latency_p95_ms,
            "latency_p99_ms": h.latency_p99_ms,
            "last_error": h.last_error,
            "circuit_state": h.circuit_state,
            "quota_remaining_pct": h.quota_remaining_pct,
            "current_key_index": h.current_key_index,
        }
        for h in healths
    ]


@providers_router.post("/{provider_id}/reset")
async def reset_provider(
    provider_id: str,
    _user: dict = Depends(require_role("admin")),
) -> dict:
    """Admin: reset circuit breaker and quota for a provider."""
    llm = get_llm()
    llm.gateway.reset_provider(provider_id)
    return {"status": "reset", "provider_id": provider_id}


# ═══════════════════════════════════════════════════════════════
#  Market Data
# ═══════════════════════════════════════════════════════════════
market_router = APIRouter(prefix="/market", tags=["Market Data"])


@market_router.get("/history")
async def get_historical_data(
    symbol: str,
    resolution: str,
    from_date: datetime,
    to_date: datetime,
    broker=Depends(get_broker),
    _user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get historical OHLCV data."""
    # Uses the injected broker adapter directly
    return await broker.get_historical_data(symbol, resolution, from_date, to_date)
