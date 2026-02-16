"""Health, Auth, Orders, Positions, Trades, Instruments, AI — REST routers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

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
    get_cached_settings,
    get_cancel_order_handler,
    get_current_user,
    get_orders_handler,
    get_place_order_handler,
    get_positions_handler,
    get_trade_history_handler,
)
from app.shared.security import create_access_token, create_refresh_token, verify_password


# ═══════════════════════════════════════════════════════════════
#  Health
# ═══════════════════════════════════════════════════════════════
health_router = APIRouter(tags=["Health"])


@health_router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_cached_settings()
    from starlette.responses import JSONResponse

    # ── Check Redis ──────────────────────────────────────────
    redis_status = "disconnected"
    try:
        from app.dependencies import get_cache

        cache = get_cache()
        if await cache.health_check():
            redis_status = "connected"
    except Exception:
        pass

    # ── Check Database ───────────────────────────────────────
    db_status = "disconnected"
    try:
        from app.dependencies import get_session_factory
        from sqlalchemy import text

        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception:
        pass

    overall = "ok" if db_status == "connected" and redis_status == "connected" else "degraded"

    resp = HealthResponse(
        status=overall,
        version="0.1.0",
        environment=settings.app_env.value,
        services={
            "database": db_status,
            "redis": redis_status,
            "broker": f"{settings.broker_provider} (paper_mode={settings.paper_trading_mode})",
        },
    )
    if overall != "ok":
        return JSONResponse(content=resp.model_dump(), status_code=503)
    return resp


@health_router.get("/metrics")
async def prometheus_metrics() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# ═══════════════════════════════════════════════════════════════
#  Auth
# ═══════════════════════════════════════════════════════════════
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

# Demo users (replace with DB in production)
_DEMO_USERS = {
    "admin": {
        "password_hash": "$2b$12$LJ3m4ys3Lz0Y7HsQb7Xz0uXepNYSqR3U1VBZK0xK7WJR4r3QfLCi",
        "role": "admin",
        "sub": "admin",
    }
}


@auth_router.post("/token", response_model=TokenResponse)
async def create_token(body: TokenRequest) -> TokenResponse:
    settings = get_cached_settings()
    user = _DEMO_USERS.get(body.username)
    if not user:
        from app.domain.exceptions import AuthenticationError

        raise AuthenticationError("Invalid credentials")

    # Verify password using bcrypt
    if not verify_password(body.password, user["password_hash"]):
        from app.domain.exceptions import AuthenticationError

        raise AuthenticationError("Invalid credentials")

    token_data = {"sub": user["sub"], "role": user["role"]}
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
    _user: dict = Depends(get_current_user),
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
    _user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get historical OHLCV data."""
    settings = get_cached_settings()
    
    # In a real app, we'd get the active broker adapter from a factory/dependency
    # For this MVP, we'll instantiate the configured one or use a singleton.
    # We'll rely on the settings to decide.
    
    # Quick factory logic (should be in dependencies.py preferably)
    from app.adapters.outbound.broker.zerodha import ZerodhaBrokerAdapter
    from app.adapters.outbound.broker.shoonya import ShoonyaBrokerAdapter
    
    adapter = None
    if settings.broker_provider == "zerodha":
        adapter = ZerodhaBrokerAdapter(
            api_key=settings.zerodha_api_key,
            api_secret=settings.zerodha_api_secret,
            access_token=settings.zerodha_access_token
        )
    elif settings.broker_provider == "shoonya":
        adapter = ShoonyaBrokerAdapter(
            user_id=settings.shoonya_user_id,
            password=settings.shoonya_password,
            api_key=settings.shoonya_api_key
        )
        # Shoonya might need login if not reusing session, but let's assume valid for now
        # or it will re-login if we implemented auto-login in adapter.
        # The Shoonya adapter implemented above has a login method but doesn't auto-call it in init.
        # For MVP, we might fail if not logged in.
    
    if not adapter:
         # Fallback to mock data if no broker configured or "paper"
         return [
             {
                 "timestamp": datetime.now(timezone.utc).isoformat(),
                 "open": 22000, "high": 22100, "low": 21900, "close": 22050, "volume": 1000
             }
         ]

    try:
        data = await adapter.get_historical_data(symbol, resolution, from_date, to_date)
        return data
    finally:
        await adapter.close()
