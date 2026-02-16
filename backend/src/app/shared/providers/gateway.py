"""Resilient provider gateway — the main entry-point for provider calls.

Composes ProviderRouter, CircuitBreaker, QuotaManager, and HealthTracker
into a single, autonomous resilience layer.  Callers simply hand in a
request function and the gateway handles rotation, failover, retries,
backoff, key rotation, and health recording — all without manual intervention.
"""

from __future__ import annotations

import asyncio
import time
import threading
from typing import Any, Awaitable, Callable, TypeVar, cast

import structlog

from app.shared.providers.circuit_breaker import CircuitBreaker
from app.shared.providers.health import ProviderHealthTracker
from app.shared.providers.quota import QuotaManager
from app.shared.providers.router import ProviderRouter
from app.shared.providers.types import ProviderConfig, ProviderHealth, RoutingStrategy

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class AllProvidersExhaustedError(Exception):
    """Raised when no provider is available after exhausting the fallback chain."""

    def __init__(self, errors: dict[str, str]) -> None:
        self.errors = errors
        providers = ", ".join(errors.keys())
        super().__init__(f"All providers exhausted: {providers}")


class ResilientProviderGateway:
    """Autonomous resilience layer that wraps any async provider call.

    Usage::

        gateway = ResilientProviderGateway(providers=[...])

        result = await gateway.execute(
            request_fn=lambda cfg, key: call_llm(key, prompt),
            estimated_tokens=2048,
        )

    The ``request_fn`` receives a ``ProviderConfig`` and the selected
    API key (str), and must return the result or raise on failure.
    """

    def __init__(
        self,
        providers: list[ProviderConfig],
        *,
        strategy: RoutingStrategy = RoutingStrategy.PRIORITY_FAILOVER,
        max_retries_per_provider: int = 2,
        backoff_base: float = 0.5,
        backoff_max: float = 8.0,
    ) -> None:
        self._providers = providers
        self._max_retries = max_retries_per_provider
        self._backoff_base = backoff_base
        self._backoff_max = backoff_max

        # Per-provider components
        self._health_trackers: dict[str, ProviderHealthTracker] = {}
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._quota_managers: dict[str, QuotaManager] = {}
        self._key_indices: dict[str, int] = {}
        self._key_lock = threading.Lock()

        for cfg in providers:
            pid = cfg.provider_id
            self._health_trackers[pid] = ProviderHealthTracker(pid)
            self._circuit_breakers[pid] = CircuitBreaker(
                pid,
                failure_threshold=cfg.cb_failure_threshold,
                cooldown_seconds=cfg.cb_cooldown_s,
            )
            self._quota_managers[pid] = QuotaManager(
                pid,
                rpm_limit=cfg.rpm_limit,
                tpm_limit=cfg.tpm_limit,
            )
            self._key_indices[pid] = 0

        # Router
        self._router = ProviderRouter(
            providers,
            strategy=strategy,
            health_trackers=self._health_trackers,
            circuit_breakers=self._circuit_breakers,
            quota_managers=self._quota_managers,
        )

    # ── Main entry-point ─────────────────────────────────────
    async def execute(
        self,
        request_fn: Callable[[ProviderConfig, str], Awaitable[T]],
        *,
        estimated_tokens: int = 0,
        preferred_provider: str | None = None,
    ) -> T:
        """Execute a request with automatic failover across providers.

        Args:
            request_fn: Async callable receiving (ProviderConfig, api_key) → result.
            estimated_tokens: Estimated token usage for quota checks.
            preferred_provider: Optional provider to try first (soft preference).

        Returns:
            The result from the first successful provider.

        Raises:
            AllProvidersExhaustedError: If every provider in the chain fails.
        """
        errors: dict[str, str] = {}
        attempted: set[str] = set()

        # Build execution order: preferred first, then fallback chain
        chain = self._build_chain(preferred_provider, estimated_tokens)

        for provider_cfg in chain:
            pid = provider_cfg.provider_id
            if pid in attempted:
                continue
            attempted.add(pid)

            # Try this provider with retries + key rotation
            # Force-cast to Awaitable to satisfy overly pedantic type checkers
            provider_coro = cast(Awaitable[Any], self._try_provider(
                provider_cfg, request_fn, estimated_tokens, errors
            ))
            provider_result = await provider_coro
            if provider_result is not _SENTINEL:
                # Emit failover metric if this wasn't the first choice
                if len(attempted) > 1:
                    logger.info(
                        "provider_failover_success",
                        provider=pid,
                        attempts=len(attempted),
                        failed_providers=list(attempted - {pid}),
                    )
                return provider_result  # type: ignore[return-value]

        raise AllProvidersExhaustedError(errors)

    # ── Provider-level attempt (with retries + key rotation) ─
    async def _try_provider(
        self,
        cfg: ProviderConfig,
        request_fn: Callable[[ProviderConfig, str], Awaitable[T]],
        estimated_tokens: int,
        errors: dict[str, str],
    ) -> T | object:
        pid = cfg.provider_id
        tracker = self._health_trackers[pid]
        cb = self._circuit_breakers[pid]
        quota = self._quota_managers[pid]

        max_attempts = min(cfg.max_retries + 1, max(len(cfg.api_keys), 1))

        for attempt in range(max_attempts):
            # Gate checks
            if not cb.can_execute():
                errors[pid] = "circuit_open"
                return _SENTINEL

            if not quota.can_accept(estimated_tokens):
                errors[pid] = "quota_exhausted"
                return _SENTINEL

            api_key = self._next_key(cfg)
            log = logger.bind(provider=pid, attempt=attempt + 1, key_idx=self._key_indices.get(pid, 0))

            start = time.monotonic()
            try:
                result = await asyncio.wait_for(
                    request_fn(cfg, api_key),
                    timeout=cfg.timeout_s,
                )
                latency_ms = (time.monotonic() - start) * 1000

                # Record success across all components
                tracker.record_success(latency_ms)
                cb.record_success()
                quota.record_usage(estimated_tokens)

                log.info("provider_request_success", latency_ms=float(f"{latency_ms:.1f}"))
                return result

            except asyncio.TimeoutError:
                latency_ms = (time.monotonic() - start) * 1000
                error_msg = f"Timeout after {cfg.timeout_s}s"
                tracker.record_failure(error_msg, latency_ms)
                cb.record_failure()
                errors[pid] = error_msg
                log.warning("provider_timeout", timeout_s=cfg.timeout_s)

            except Exception as exc:
                latency_ms = (time.monotonic() - start) * 1000
                error_msg = f"{type(exc).__name__}: {exc}"
                tracker.record_failure(error_msg, latency_ms)
                cb.record_failure()
                errors[pid] = error_msg
                log.warning("provider_request_failed", error=error_msg, latency_ms=float(f"{latency_ms:.1f}"))

            # Backoff before next attempt (within same provider)
            if attempt < max_attempts - 1:
                delay = min(
                    self._backoff_base * (2 ** attempt),
                    self._backoff_max,
                )
                await asyncio.sleep(delay)

        return _SENTINEL

    # ── Key rotation ─────────────────────────────────────────
    def _next_key(self, cfg: ProviderConfig) -> str:
        if not cfg.api_keys:
            return ""
        with self._key_lock:
            idx = self._key_indices.get(cfg.provider_id, 0)
            key = cfg.api_keys[idx % len(cfg.api_keys)]
            self._key_indices[cfg.provider_id] = (idx + 1) % len(cfg.api_keys)
            return key

    # ── Chain building ───────────────────────────────────────
    def _build_chain(
        self, preferred: str | None, estimated_tokens: int
    ) -> list[ProviderConfig]:
        """Build the ordered list of providers to try."""
        chain = self._router.get_fallback_chain(estimated_tokens=estimated_tokens)

        if preferred:
            # Move preferred to the front if available
            preferred_cfg = next(
                (c for c in chain if c.provider_id == preferred), None
            )
            if preferred_cfg:
                chain.remove(preferred_cfg)
                chain.insert(0, preferred_cfg)

        return chain

    # ── Health observation ───────────────────────────────────
    def get_health(self, provider_id: str) -> ProviderHealth | None:
        tracker = self._health_trackers.get(provider_id)
        if not tracker:
            return None
        health = tracker.health
        # Enrich with circuit + quota state
        cb = self._circuit_breakers.get(provider_id)
        if cb:
            health.circuit_state = cb.state.value
        quota = self._quota_managers.get(provider_id)
        if quota:
            health.quota_remaining_pct = quota.remaining_pct
        key_idx = self._key_indices.get(provider_id, 0)
        health.current_key_index = key_idx
        return health

    def get_all_health(self) -> list[ProviderHealth]:
        results: list[ProviderHealth] = []
        for pid in self._health_trackers:
            h = self.get_health(pid)
            if h is not None:
                results.append(h)
        return results

    def reset_provider(self, provider_id: str) -> None:
        """Admin reset — clears circuit breaker and quota for a provider."""
        if cb := self._circuit_breakers.get(provider_id):
            cb.reset()
        if quota := self._quota_managers.get(provider_id):
            quota.reset()
        logger.info("provider_admin_reset", provider=provider_id)


# Sentinel for "no result"
_SENTINEL = object()
