"""FastAPI application entry-point.

Assembles routers, middleware, exception handlers, and lifecycle hooks.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.adapters.inbound.rest.routers import (
    ai_router,
    auth_router,
    health_router,
    orders_router,
    positions_router,
    providers_router,
    trades_router,
    market_router,
)
from app.adapters.inbound.ws import ws_router
from app.config import Settings, get_settings
from app.shared.errors import register_exception_handlers
from app.shared.middleware import (
    LoggingMiddleware,
    MetricsMiddleware,
    RateLimitMiddleware,
    RequestIdMiddleware,
)
from app.shared.observability import configure_logging

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifecycle — startup & shutdown hooks."""
    settings: Settings = app.state.settings
    configure_logging(
        log_level=settings.log_level,
        json_logs=settings.is_production,
    )
    logger.info(
        "application_starting",
        env=settings.app_env.value,
        paper_mode=settings.paper_trading_mode,
    )
    yield
    # Shutdown: close external connections
    from app.dependencies import get_cache, get_llm

    try:
        await get_cache().close()
    except Exception:
        pass
    try:
        await get_llm().close()
    except Exception:
        pass
    logger.info("application_shutdown")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory — creates a fully configured FastAPI instance."""
    settings = settings or get_settings()

    app = FastAPI(
        title="AI Trading Platform",
        description=(
            "AI-Native Option Trading Platform for the Indian Stock Market. "
            "Provides REST and WebSocket APIs for order management, position tracking, "
            "AI-driven analysis, and real-time market data streaming."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # Store settings in app state for lifecycle access
    app.state.settings = settings

    # ── Middleware (order matters: first added = outermost) ───
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware, max_requests=200, window_seconds=60)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)

    # ── Exception handlers ───────────────────────────────────
    register_exception_handlers(app)

    # ── REST routers (versioned) ─────────────────────────────
    api_v1 = "/api/v1"
    app.include_router(health_router, prefix=api_v1)
    app.include_router(auth_router, prefix=api_v1)
    app.include_router(orders_router, prefix=api_v1)
    app.include_router(positions_router, prefix=api_v1)
    app.include_router(trades_router, prefix=api_v1)
    app.include_router(ai_router, prefix=api_v1)
    app.include_router(providers_router, prefix=api_v1)
    app.include_router(market_router, prefix=api_v1)

    # ── WebSocket routers ────────────────────────────────────
    app.include_router(ws_router)

    return app


# Uvicorn entry-point
app = create_app()
