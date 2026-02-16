"""Core types for the multi-provider resilience framework."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class ProviderStatus(str, enum.Enum):
    """Health status of an API provider."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CIRCUIT_OPEN = "circuit_open"


class RoutingStrategy(str, enum.Enum):
    """How the router selects the next provider."""

    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    PRIORITY_FAILOVER = "priority_failover"
    LEAST_LATENCY = "least_latency"


@dataclass(frozen=True)
class ProviderConfig:
    """Static configuration for a single provider.

    Attributes:
        provider_id:  Unique identifier (e.g. "anthropic", "openai").
        api_keys:     Pool of API keys to rotate through.
        priority:     Lower = higher priority (used in PRIORITY_FAILOVER).
        weight:       Relative weight (used in WEIGHTED routing).
        rpm_limit:    Max requests per minute (0 = unlimited).
        tpm_limit:    Max tokens per minute (0 = unlimited).
        timeout_s:    Per-request timeout in seconds.
        cb_failure_threshold: Consecutive failures before circuit opens.
        cb_cooldown_s:        Seconds before half-open probe.
        max_retries:  Max retries within this single provider.
        metadata:     Arbitrary extra config (model name, base URL, etc.).
    """

    provider_id: str
    api_keys: tuple[str, ...] = ()
    priority: int = 10
    weight: int = 1
    rpm_limit: int = 60
    tpm_limit: int = 0
    timeout_s: float = 60.0
    cb_failure_threshold: int = 5
    cb_cooldown_s: float = 30.0
    max_retries: int = 2
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def has_keys(self) -> bool:
        return bool(self.api_keys) and any(k.strip() for k in self.api_keys)


@dataclass
class ProviderHealth:
    """Read-only snapshot of a provider's current health."""

    provider_id: str
    status: ProviderStatus = ProviderStatus.HEALTHY
    total_requests: int = 0
    total_successes: int = 0
    total_failures: int = 0
    consecutive_failures: int = 0
    success_rate: float = 1.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    latency_p99_ms: float = 0.0
    last_error: str | None = None
    last_error_time: float | None = None
    circuit_state: str = "closed"
    quota_remaining_pct: float = 100.0
    current_key_index: int = 0
