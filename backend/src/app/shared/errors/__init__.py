"""Global exception handlers — map domain errors to HTTP responses."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse
import structlog

from app.domain.exceptions import (
    AuthenticationError,
    AuthorisationError,
    BrokerError,
    DomainError,
    KillSwitchActivatedError,
    LLMError,
    OrderNotFoundError,
    RiskLimitExceededError,
    ValidationError,
)

logger = structlog.get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all domain→HTTP exception mappings."""

    @app.exception_handler(ValidationError)
    async def handle_validation(request: Request, exc: ValidationError) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=422,
            content={"code": exc.code, "message": exc.message},
        )

    @app.exception_handler(OrderNotFoundError)
    async def handle_not_found(request: Request, exc: OrderNotFoundError) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=404,
            content={"code": exc.code, "message": exc.message},
        )

    @app.exception_handler(RiskLimitExceededError)
    async def handle_risk(request: Request, exc: RiskLimitExceededError) -> ORJSONResponse:
        logger.warning("risk_limit_http", message=exc.message)
        return ORJSONResponse(
            status_code=403,
            content={"code": exc.code, "message": exc.message},
        )

    @app.exception_handler(KillSwitchActivatedError)
    async def handle_kill_switch(
        request: Request, exc: KillSwitchActivatedError
    ) -> ORJSONResponse:
        logger.critical("kill_switch_http", message=exc.message)
        return ORJSONResponse(
            status_code=503,
            content={"code": exc.code, "message": exc.message},
        )

    @app.exception_handler(AuthenticationError)
    async def handle_authn(request: Request, exc: AuthenticationError) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=401,
            content={"code": exc.code, "message": exc.message},
        )

    @app.exception_handler(AuthorisationError)
    async def handle_authz(request: Request, exc: AuthorisationError) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=403,
            content={"code": exc.code, "message": exc.message},
        )

    @app.exception_handler(BrokerError)
    async def handle_broker(request: Request, exc: BrokerError) -> ORJSONResponse:
        logger.error("broker_error_http", message=exc.message)
        return ORJSONResponse(
            status_code=502,
            content={"code": exc.code, "message": exc.message},
        )

    @app.exception_handler(LLMError)
    async def handle_llm(request: Request, exc: LLMError) -> ORJSONResponse:
        logger.error("llm_error_http", message=exc.message)
        return ORJSONResponse(
            status_code=502,
            content={"code": exc.code, "message": exc.message},
        )

    @app.exception_handler(DomainError)
    async def handle_domain(request: Request, exc: DomainError) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=400,
            content={"code": exc.code, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> ORJSONResponse:
        logger.exception("unhandled_exception", error=str(exc))
        return ORJSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        )
