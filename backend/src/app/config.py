"""AI Trading Platform — Application Configuration."""

from __future__ import annotations

import enum
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, enum.Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Centralised, validated configuration loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────
    app_name: str = "ai-trading-platform"
    app_env: Environment = Environment.DEVELOPMENT
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # ── Security ─────────────────────────────────────────────
    jwt_secret_key: str = "CHANGE-ME"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    api_key_header: str = "X-API-Key"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # ── Database ─────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/trading_platform"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # ── Redis ────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50

    # ── Broker ───────────────────────────────────────────────
    broker_provider: str = "paper"
    dhan_client_id: str = ""
    dhan_access_token: str = ""
    shoonya_user_id: str = ""
    shoonya_password: str = ""
    shoonya_api_key: str = ""
    zerodha_api_key: str = ""
    zerodha_api_secret: str = ""

    # ── LLM ──────────────────────────────────────────────────
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""

    # Multiple keys per provider (comma-separated for rotation)
    anthropic_api_keys: str = ""
    openai_api_keys: str = ""
    google_api_keys: str = ""

    # ── Provider Resilience ──────────────────────────────────
    llm_routing_strategy: str = "priority_failover"
    llm_provider_priority: str = "google,anthropic,openai"

    # Circuit breaker
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_cooldown_seconds: float = 30.0

    # Per-provider rate limits (requests per minute)
    anthropic_rpm: int = 50
    openai_rpm: int = 60
    google_rpm: int = 60
    anthropic_tpm: int = 0  # 0 = unlimited
    openai_tpm: int = 0
    google_tpm: int = 0

    # Gateway settings
    provider_timeout_seconds: float = 60.0
    provider_backoff_base: float = 0.5
    provider_backoff_max: float = 8.0

    # ── Observability ────────────────────────────────────────
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "ai-trading-platform"
    prometheus_enabled: bool = True

    # ── Trading Guardrails ───────────────────────────────────
    max_order_value_inr: int = 500_000
    max_position_delta: float = 100.0
    max_orders_per_minute: int = 10
    kill_switch_drawdown_pct: float = 5.0
    paper_trading_mode: bool = True

    # ── Derived helpers ──────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, v: str) -> str:
        return v.upper()

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, v: str) -> str:
        if not v.startswith(("postgresql", "sqlite")):
            raise ValueError("database_url must start with 'postgresql' or 'sqlite'")
        return v

    @model_validator(mode="after")
    def _guard_production_secrets(self) -> Settings:
        """Prevent production from running with insecure defaults."""
        if self.app_env == Environment.PRODUCTION:
            if self.jwt_secret_key in ("CHANGE-ME", ""):
                raise ValueError(
                    "jwt_secret_key must be set to a secure value in production"
                )
            if self.paper_trading_mode:
                import warnings
                warnings.warn(
                    "paper_trading_mode is ON in production — set to false for live trading",
                    UserWarning,
                    stacklevel=2,
                )
        return self


def get_settings(**overrides: Any) -> Settings:
    """Factory that allows test-time overrides."""
    return Settings(**overrides)
