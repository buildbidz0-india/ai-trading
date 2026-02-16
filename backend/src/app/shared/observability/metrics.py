"""Prometheus metrics for the trading platform."""

from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge


# ── HTTP metrics ─────────────────────────────────────────────
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# ── Trading metrics ──────────────────────────────────────────
ORDERS_TOTAL = Counter(
    "orders_total",
    "Total orders processed",
    ["side", "order_type", "status"],
)

TRADES_TOTAL = Counter(
    "trades_total",
    "Total trades executed",
    ["side"],
)

OPEN_POSITIONS = Gauge(
    "open_positions",
    "Number of currently open positions",
)

PORTFOLIO_PNL = Gauge(
    "portfolio_pnl_inr",
    "Current portfolio P&L in INR",
    ["type"],  # realised / unrealised
)

# ── AI agent metrics ─────────────────────────────────────────
AGENT_INVOCATIONS = Counter(
    "ai_agent_invocations_total",
    "Total AI agent invocations",
    ["agent_role", "provider", "status"],
)

AGENT_LATENCY = Histogram(
    "ai_agent_latency_seconds",
    "AI agent response latency",
    ["agent_role", "provider"],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
)

# ── Risk metrics ─────────────────────────────────────────────
RISK_REJECTIONS = Counter(
    "risk_rejections_total",
    "Orders rejected by risk engine",
    ["reason_code"],
)

GUARDRAIL_VIOLATIONS = Counter(
    "guardrail_violations_total",
    "Orders flagged by guardrails",
)
