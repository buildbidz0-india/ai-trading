"""FastAPI middleware stack — request ID, logging, metrics, rate limiting."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Awaitable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.shared.observability.metrics import HTTP_REQUEST_DURATION, HTTP_REQUESTS_TOTAL

logger = structlog.get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Injects a unique X-Request-ID header into every request/response."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        structlog.contextvars.unbind_contextvars("request_id")
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with method, path, status, and duration."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(float(duration * 1000), 2),
            client=request.client.host if request.client else "unknown",
        )
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collects Prometheus HTTP metrics."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start

        # Normalize path to avoid high cardinality
        path = request.url.path
        if "/api/" in path:
            # Keep the first 3 segments: /api/v1/resource
            parts = path.split("/")
            path = "/".join(parts[:5]) if len(parts) > 4 else path

        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=path,
            status_code=response.status_code,
        ).inc()

        HTTP_REQUEST_DURATION.labels(
            method=request.method,
            endpoint=path,
        ).observe(duration)

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter backed by Redis.

    Uses CachePort.increment() for distributed counting across workers.
    Falls back to allowing the request if Redis is unavailable.
    """

    def __init__(self, app: object, max_requests: int = 100, window_seconds: int = 60) -> None:  # type: ignore[override]
        super().__init__(app)  # type: ignore[arg-type]
        self._max = max_requests
        self._window = window_seconds

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        client_ip = request.client.host if request.client else "unknown"

        # Use Redis for distributed rate limiting
        try:
            from app.dependencies import get_cache

            cache = get_cache()
            key = f"rate_limit:{client_ip}"
            count = await cache.increment(key, ttl_seconds=self._window)

            if count > self._max:
                return Response(
                    content='{"code":"RATE_LIMITED","message":"Too many requests"}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": str(self._window)},
                )
        except Exception:
            # If Redis is unavailable, allow the request (fail-open)
            logger.warning("rate_limit_redis_unavailable", client_ip=client_ip)

        return await call_next(request)
