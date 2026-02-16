"""Provider router — selects the best available provider based on strategy.

Filters out unhealthy, circuit-open, and quota-exhausted providers,
then applies the configured routing strategy to the remaining candidates.
"""

from __future__ import annotations

import random
import threading
from typing import Sequence

import structlog

from app.shared.providers.circuit_breaker import CircuitBreaker
from app.shared.providers.health import ProviderHealthTracker
from app.shared.providers.quota import QuotaManager
from app.shared.providers.types import ProviderConfig, ProviderStatus, RoutingStrategy

logger = structlog.get_logger(__name__)


class ProviderRouter:
    """Selects the best available provider from a pool."""

    def __init__(
        self,
        providers: Sequence[ProviderConfig],
        *,
        strategy: RoutingStrategy = RoutingStrategy.PRIORITY_FAILOVER,
        health_trackers: dict[str, ProviderHealthTracker] | None = None,
        circuit_breakers: dict[str, CircuitBreaker] | None = None,
        quota_managers: dict[str, QuotaManager] | None = None,
    ) -> None:
        self._providers = list(providers)
        self._strategy = strategy
        self._health = health_trackers or {}
        self._circuits = circuit_breakers or {}
        self._quotas = quota_managers or {}

        # Round-robin state
        self._rr_index = 0
        self._lock = threading.Lock()

    @property
    def strategy(self) -> RoutingStrategy:
        return self._strategy

    def select_provider(
        self,
        *,
        exclude: set[str] | None = None,
        estimated_tokens: int = 0,
    ) -> ProviderConfig | None:
        """Select the best available provider, excluding any in the exclude set."""
        exclude = exclude or set()
        candidates = self._filter_candidates(exclude, estimated_tokens)

        if not candidates:
            logger.warning(
                "no_available_providers",
                strategy=self._strategy.value,
                excluded=list(exclude),
                total_configured=len(self._providers),
            )
            return None

        if self._strategy == RoutingStrategy.PRIORITY_FAILOVER:
            return self._select_priority(candidates)
        elif self._strategy == RoutingStrategy.ROUND_ROBIN:
            return self._select_round_robin(candidates)
        elif self._strategy == RoutingStrategy.WEIGHTED:
            return self._select_weighted(candidates)
        elif self._strategy == RoutingStrategy.LEAST_LATENCY:
            return self._select_least_latency(candidates)
        else:
            return candidates[0]

    def get_fallback_chain(
        self,
        *,
        exclude: set[str] | None = None,
        estimated_tokens: int = 0,
    ) -> list[ProviderConfig]:
        """Get all available providers in priority order for failover."""
        exclude = exclude or set()
        candidates = self._filter_candidates(exclude, estimated_tokens)
        # Always sort by priority for failover chain
        return sorted(candidates, key=lambda p: p.priority)

    # ── Strategy implementations ─────────────────────────────
    def _select_priority(self, candidates: list[ProviderConfig]) -> ProviderConfig:
        return min(candidates, key=lambda p: p.priority)

    def _select_round_robin(self, candidates: list[ProviderConfig]) -> ProviderConfig:
        with self._lock:
            idx = self._rr_index % len(candidates)
            self._rr_index += 1
            return candidates[idx]

    def _select_weighted(self, candidates: list[ProviderConfig]) -> ProviderConfig:
        weights = [p.weight for p in candidates]
        return random.choices(candidates, weights=weights, k=1)[0]

    def _select_least_latency(self, candidates: list[ProviderConfig]) -> ProviderConfig:
        def latency_key(p: ProviderConfig) -> float:
            tracker = self._health.get(p.provider_id)
            if tracker:
                h = tracker.health
                return h.latency_p50_ms if h.latency_p50_ms > 0 else float("inf")
            return float("inf")

        return min(candidates, key=latency_key)

    # ── Filtering ────────────────────────────────────────────
    def _filter_candidates(
        self, exclude: set[str], estimated_tokens: int
    ) -> list[ProviderConfig]:
        candidates: list[ProviderConfig] = []

        for provider in self._providers:
            pid = provider.provider_id

            # Skip explicitly excluded
            if pid in exclude:
                continue

            # Skip providers without API keys
            if not provider.has_keys:
                continue

            # Skip circuit-open providers
            cb = self._circuits.get(pid)
            if cb and not cb.can_execute():
                logger.debug("provider_circuit_open", provider=pid)
                continue

            # Skip unhealthy providers
            tracker = self._health.get(pid)
            if tracker and tracker.status == ProviderStatus.UNHEALTHY:
                logger.debug("provider_unhealthy", provider=pid)
                continue

            # Skip quota-exhausted providers
            quota = self._quotas.get(pid)
            if quota and not quota.can_accept(estimated_tokens):
                logger.debug("provider_quota_exhausted", provider=pid)
                continue

            candidates.append(provider)

        return candidates
