"""Resilient provider gateway — the main entry-point for provider calls.

Composes ProviderRouter, KeyManager, and HealthTracker into a single, autonomous
resilience layer.  Callers simply hand in a request function and the gateway
handles rotation, failover, retries, backoff, key rotation, and health recording
— all without manual intervention.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, TypeVar, cast

import structlog

from app.shared.providers.key_manager import KeyManager
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
        self._key_managers: dict[str, KeyManager] = {}

        for cfg in providers:
            pid = cfg.provider_id
            self._key_managers[pid] = KeyManager(cfg)

        # Router
        self._router = ProviderRouter(
            providers,
            strategy=strategy,
            key_managers=self._key_managers,
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
        km = self._key_managers[pid]

        # Use provider-defined max retries or fallback to default
        max_attempts = min(cfg.max_retries + 1, max(km.key_count, 1))

        # Loop through attempts, rotating keys each time
        for attempt in range(max_attempts):
            # Select a usable key
            key_state = km.select_key(estimated_tokens)

            if not key_state:
                # No usable keys (all circuit open or quota exhausted)
                # If it's the first attempt, we fail immediately
                # If we've tried some keys and failed, we also stop here
                errors[pid] = "no_usable_keys"
                # Log detailed reasons why keys are unusable
                logger.warning(
                    "provider_keys_exhausted",
                    provider=pid,
                    reasons=km.get_exhausted_errors()
                )
                return _SENTINEL

            log = logger.bind(provider=pid, attempt=attempt + 1, key_idx=key_state.index)

            start = time.monotonic()
            try:
                result = await asyncio.wait_for(
                    request_fn(cfg, key_state.api_key),
                    timeout=cfg.timeout_s,
                )
                latency_ms = (time.monotonic() - start) * 1000

                # Record success
                km.record_success(key_state.index, latency_ms, estimated_tokens)
                
                log.info("provider_request_success", latency_ms=float(f"{latency_ms:.1f}"))
                return result

            except asyncio.TimeoutError:
                latency_ms = (time.monotonic() - start) * 1000
                error_msg = f"Timeout after {cfg.timeout_s}s"
                km.record_failure(key_state.index, error_msg, latency_ms)
                # Specific error for this attempt, but we might retry with another key
                log.warning("provider_timeout", timeout_s=cfg.timeout_s, key_idx=key_state.index)

            except Exception as exc:
                latency_ms = (time.monotonic() - start) * 1000
                error_msg = f"{type(exc).__name__}: {exc}"
                km.record_failure(key_state.index, error_msg, latency_ms)
                log.warning("provider_request_failed", error=error_msg, latency_ms=float(f"{latency_ms:.1f}"), key_idx=key_state.index)

            # Backoff before next attempt (if we still have retries left)
            if attempt < max_attempts - 1:
                delay = min(
                    self._backoff_base * (2 ** attempt),
                    self._backoff_max,
                )
                await asyncio.sleep(delay)

        errors[pid] = "exhausted_attempts"
        return _SENTINEL

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
        km = self._key_managers.get(provider_id)
        if not km:
            return None
        
        # Aggregate health? Or return first key health?
        # Ideally, we return provider-level aggregate health.
        # For backward compatibility, we can aggregate.
        
        # Simple aggregation: sum requests, successes, failures.
        # Latency: complex without raw data. Avg of avgs?
        # Status: UNHEALTHY if ALL keys unhealthy, else HEALTHY/DEGRADED.
        
        # TODO: Implement proper aggregation in KeyManager then expose here.
        # For now, simplistic placeholder based on internal key lists.
        # This is strictly for monitoring/observability compatibility.
        
        total_req = 0
        total_succ = 0
        total_fail = 0
        
        usable_keys = 0
        
        for ks in km._keys:
            h = ks.health_tracker.health
            total_req += h.total_requests
            total_succ += h.total_successes
            total_fail += h.total_failures
            if ks.circuit_breaker.can_execute():
                usable_keys += 1
                
        status = "healthy"
        if usable_keys == 0 and km.key_count > 0:
            status = "unhealthy"
        elif usable_keys < km.key_count:
            status = "degraded"
            
        success_rate = (total_succ / total_req) if total_req > 0 else 1.0
        
        return ProviderHealth(
            provider_id=provider_id,
            status=status,
            total_requests=total_req,
            total_successes=total_succ,
            total_failures=total_fail,
            success_rate=float(f"{success_rate:.4f}"),
            # P50/95/99 hard to aggregate without raw samples, zeroing for now or needs improvement
            latency_p50_ms=0.0,
            latency_p95_ms=0.0,
            latency_p99_ms=0.0,
            last_error="Check individual key logs",
            quota_remaining_pct=100.0, # Approximate
            current_key_index=km._rr_index,
        )

    def get_all_health(self) -> list[ProviderHealth]:
        results: list[ProviderHealth] = []
        for pid in self._key_managers:
            h = self.get_health(pid)
            if h is not None:
                results.append(h)
        return results


# Sentinel for "no result"
_SENTINEL = object()
