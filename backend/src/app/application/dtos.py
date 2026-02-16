"""Data Transfer Objects — Pydantic models for API boundaries.

DTOs handle serialisation, validation, and documentation.  They live in the
application layer because they are *not* domain objects — they adapt between
the external world and the domain.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ═══════════════════════════════════════════════════════════════
#  Common
# ═══════════════════════════════════════════════════════════════
class PaginationParams(BaseModel):
    offset: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=500)


class PaginatedResponse(BaseModel):
    total: int
    offset: int
    limit: int
    items: list[dict]  # type: ignore[type-arg]


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict | None = None  # type: ignore[type-arg]


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    environment: str = "development"
    services: dict[str, str] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
#  Auth
# ═══════════════════════════════════════════════════════════════
class TokenRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ═══════════════════════════════════════════════════════════════
#  Orders
# ═══════════════════════════════════════════════════════════════
class PlaceOrderRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    symbol: str = Field(..., min_length=1, max_length=30, examples=["NIFTY"])
    exchange: str = Field("NFO", examples=["NFO", "NSE", "BSE"])
    side: str = Field(..., pattern="^(BUY|SELL)$")
    order_type: str = Field("MARKET", pattern="^(MARKET|LIMIT|STOP_LOSS|STOP_LOSS_LIMIT)$")
    product_type: str = Field("NRML", pattern="^(CNC|MIS|NRML)$")
    quantity: int = Field(..., gt=0, le=5000)
    price: Decimal = Field(Decimal("0"), ge=0)
    trigger_price: Decimal = Field(Decimal("0"), ge=0)
    source: str = Field("MANUAL", pattern="^(MANUAL|AI_AGENT|SYSTEM)$")


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    symbol: str
    exchange: str
    side: str
    order_type: str
    product_type: str
    quantity: int
    price: str
    status: str
    broker_order_id: str | None = None
    rejection_reason: str | None = None
    source: str
    created_at: datetime
    updated_at: datetime


class CancelOrderRequest(BaseModel):
    order_id: str = Field(..., min_length=1)


# ═══════════════════════════════════════════════════════════════
#  Positions
# ═══════════════════════════════════════════════════════════════
class PositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    instrument_id: str
    symbol: str
    exchange: str
    net_quantity: int
    average_price: str
    realised_pnl: str
    unrealised_pnl: str
    greeks: dict[str, float] = Field(default_factory=dict)
    updated_at: datetime


# ═══════════════════════════════════════════════════════════════
#  Trades
# ═══════════════════════════════════════════════════════════════
class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_id: str
    symbol: str
    exchange: str
    side: str
    quantity: int
    price: str
    fees: str
    executed_at: datetime


# ═══════════════════════════════════════════════════════════════
#  Option Chain
# ═══════════════════════════════════════════════════════════════
class OptionChainEntryResponse(BaseModel):
    strike_price: str
    call_price: str
    put_price: str
    call_oi: int
    put_oi: int
    call_volume: int
    put_volume: int
    call_iv: float
    put_iv: float
    call_greeks: dict[str, float]
    put_greeks: dict[str, float]


class OptionChainResponse(BaseModel):
    symbol: str
    expiry: str
    underlying_price: str
    max_pain: str | None
    entries: list[OptionChainEntryResponse]
    timestamp: datetime


# ═══════════════════════════════════════════════════════════════
#  Instruments
# ═══════════════════════════════════════════════════════════════
class InstrumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    symbol: str
    exchange: str
    instrument_type: str
    lot_size: int
    tick_size: str
    option_type: str | None
    strike_price: str | None
    expiry: str | None


# ═══════════════════════════════════════════════════════════════
#  AI Analysis
# ═══════════════════════════════════════════════════════════════
class AIAnalysisRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=30)
    context: str = Field("", max_length=5000)


class AgentOutput(BaseModel):
    agent_role: str
    provider: str
    confidence: float = Field(ge=0.0, le=1.0)
    latency_ms: float
    summary: str
    raw_output: dict | None = None  # type: ignore[type-arg]


class AIAnalysisResponse(BaseModel):
    symbol: str
    agents: list[AgentOutput]
    recommended_action: str | None = None
    overall_confidence: float = 0.0
    timestamp: datetime
