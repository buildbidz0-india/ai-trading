"""Provider router — selects the best available provider based on strategy.

Filters out unhealthy, circuit-open, and quota-exhausted providers,
then applies the configured routing strategy to the remaining candidates.
"""

from __future__ import annotations

import random
import threading
from typing import Sequence

import structlog

from app.shared.providers.key_manager import KeyManager
from app.shared.providers.types import ProviderConfig, RoutingStrategy

logger = structlog.get_logger(__name__)


class ProviderRouter:
    """Selects the best available provider from a pool."""

    def __init__(
        self,
        providers: Sequence[ProviderConfig],
        *,
        strategy: RoutingStrategy = RoutingStrategy.PRIORITY_FAILOVER,
        key_managers: dict[str, KeyManager] | None = None,
    ) -> None:
        self._providers = list(providers)
        self._strategy = strategy
        self._key_managers = key_managers or {}

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
            # We don't have detailed reasoning here easily, but KeyManagers logged warnings already potentially
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
        # TODO: Implement complex latency with KeyManager aggregator later
        # For now, simplistic fallback or random as latency might be distributed across keys
        return candidates[0] # Simplification for now

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
            
            # Check availability via KeyManager
            km = self._key_managers.get(pid)
            if not km:
                continue
            
            # KeyManager determines if there are ANY usable keys
            # Ideally we check estimated_tokens too, but selecting a key is dynamic.
            # We ask "is there at least one potentially usable key?"
            # For simplicity, we can rely on KeyManager internal logic.
            # But here we just want to know "is the provider COMPLETELY dead?"
            if not km.any_healthy:
                logger.debug("provider_all_keys_unhealthy", provider=pid)
                continue
            
            candidates.append(provider)

        return candidates
