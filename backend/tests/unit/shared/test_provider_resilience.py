"""Comprehensive tests for the multi-provider resilience system.

Tests cover all 5 core components: ProviderHealthTracker, CircuitBreaker,
QuotaManager, ProviderRouter, and ResilientProviderGateway.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

import pytest

from app.shared.providers.circuit_breaker import CircuitBreaker, CircuitState
from app.shared.providers.gateway import AllProvidersExhaustedError, ResilientProviderGateway
from app.shared.providers.health import ProviderHealthTracker
from app.shared.providers.quota import QuotaManager
from app.shared.providers.router import ProviderRouter
from app.shared.providers.types import ProviderConfig, ProviderHealth, ProviderStatus, RoutingStrategy


# ═══════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════
@pytest.fixture
def provider_configs() -> list[ProviderConfig]:
    return [
        ProviderConfig(
            provider_id="alpha",
            api_keys=("key-a1", "key-a2"),
            priority=1,
            weight=3,
            rpm_limit=10,
            cb_failure_threshold=3,
            cb_cooldown_s=1.0,
        ),
        ProviderConfig(
            provider_id="beta",
            api_keys=("key-b1",),
            priority=2,
            weight=1,
            rpm_limit=10,
            cb_failure_threshold=3,
            cb_cooldown_s=1.0,
        ),
        ProviderConfig(
            provider_id="gamma",
            api_keys=("key-g1",),
            priority=3,
            weight=1,
            rpm_limit=10,
            cb_failure_threshold=3,
            cb_cooldown_s=1.0,
        ),
    ]


# ═══════════════════════════════════════════════════════════════
#  ProviderHealthTracker
# ═══════════════════════════════════════════════════════════════
class TestProviderHealthTracker:
    def test_starts_healthy(self) -> None:
        tracker = ProviderHealthTracker("test")
        assert tracker.status == ProviderStatus.HEALTHY
        h = tracker.health
        assert h.success_rate == 1.0
        assert h.total_requests == 0

    def test_records_success(self) -> None:
        tracker = ProviderHealthTracker("test")
        tracker.record_success(100.0)
        tracker.record_success(200.0)
        h = tracker.health
        assert h.total_requests == 2
        assert h.total_successes == 2
        assert h.total_failures == 0
        assert h.consecutive_failures == 0
        assert h.success_rate == 1.0

    def test_records_failure(self) -> None:
        tracker = ProviderHealthTracker("test")
        tracker.record_failure("timeout", 500.0)
        h = tracker.health
        assert h.total_failures == 1
        assert h.consecutive_failures == 1
        assert h.last_error == "timeout"

    def test_success_resets_consecutive_failures(self) -> None:
        tracker = ProviderHealthTracker("test")
        tracker.record_failure("err1")
        tracker.record_failure("err2")
        assert tracker.consecutive_failures == 2
        tracker.record_success(50.0)
        assert tracker.consecutive_failures == 0

    def test_degraded_status(self) -> None:
        tracker = ProviderHealthTracker("test", degraded_threshold=0.30)
        # 7 successes, 3 failures = 30% failure rate → degraded
        for _ in range(7):
            tracker.record_success(50.0)
        for _ in range(3):
            tracker.record_failure("err")
        assert tracker.status == ProviderStatus.DEGRADED

    def test_unhealthy_status(self) -> None:
        tracker = ProviderHealthTracker("test", unhealthy_threshold=0.60)
        # 4 successes, 6 failures = 60% failure rate → unhealthy
        for _ in range(4):
            tracker.record_success(50.0)
        for _ in range(6):
            tracker.record_failure("err")
        assert tracker.status == ProviderStatus.UNHEALTHY

    def test_latency_percentiles(self) -> None:
        tracker = ProviderHealthTracker("test")
        latencies = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        for lat in latencies:
            tracker.record_success(float(lat))
        h = tracker.health
        assert h.latency_p50_ms > 0
        assert h.latency_p95_ms >= h.latency_p50_ms

    def test_sliding_window_eviction(self) -> None:
        tracker = ProviderHealthTracker("test", window_seconds=0.1)
        tracker.record_failure("err")
        assert tracker.status != ProviderStatus.HEALTHY or tracker.health.total_failures == 1
        time.sleep(0.15)
        # After window expires, status should return to HEALTHY
        assert tracker.status == ProviderStatus.HEALTHY


# ═══════════════════════════════════════════════════════════════
#  CircuitBreaker
# ═══════════════════════════════════════════════════════════════
class TestCircuitBreaker:
    def test_starts_closed(self) -> None:
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_opens_after_threshold(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_does_not_open_before_threshold(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=5)
        for _ in range(4):
            cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_after_cooldown(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=2, cooldown_seconds=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_to_closed_on_success(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=2, cooldown_seconds=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.can_execute() is True
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_to_open_on_failure(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=2, cooldown_seconds=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_failure_count(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        # Should now need 3 more failures to open
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_force_reset(self) -> None:
        cb = CircuitBreaker("test", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True


# ═══════════════════════════════════════════════════════════════
#  QuotaManager
# ═══════════════════════════════════════════════════════════════
class TestQuotaManager:
    def test_starts_with_full_quota(self) -> None:
        qm = QuotaManager("test", rpm_limit=10)
        assert qm.can_accept() is True
        assert qm.remaining_pct == 100.0
        assert qm.requests_in_window == 0

    def test_accepts_within_limit(self) -> None:
        qm = QuotaManager("test", rpm_limit=5)
        for _ in range(4):
            assert qm.can_accept() is True
            qm.record_usage()
        assert qm.can_accept() is True  # 4 out of 5

    def test_rejects_at_limit(self) -> None:
        qm = QuotaManager("test", rpm_limit=3)
        for _ in range(3):
            qm.record_usage()
        assert qm.can_accept() is False

    def test_sliding_window_replenishes(self) -> None:
        qm = QuotaManager("test", rpm_limit=2, window_seconds=0.1)
        qm.record_usage()
        qm.record_usage()
        assert qm.can_accept() is False
        time.sleep(0.15)
        assert qm.can_accept() is True

    def test_tpm_limit(self) -> None:
        qm = QuotaManager("test", rpm_limit=100, tpm_limit=1000)
        qm.record_usage(tokens=800)
        # Only 200 tokens left, request for 300 should fail
        assert qm.can_accept(estimated_tokens=300) is False
        assert qm.can_accept(estimated_tokens=200) is True

    def test_remaining_pct(self) -> None:
        qm = QuotaManager("test", rpm_limit=10)
        qm.record_usage()
        qm.record_usage()
        assert qm.remaining_pct == 80.0

    def test_unlimited_rpm(self) -> None:
        qm = QuotaManager("test", rpm_limit=0)
        for _ in range(1000):
            qm.record_usage()
        assert qm.can_accept() is True
        assert qm.remaining_pct == 100.0

    def test_force_reset(self) -> None:
        qm = QuotaManager("test", rpm_limit=2)
        qm.record_usage()
        qm.record_usage()
        assert qm.can_accept() is False
        qm.reset()
        assert qm.can_accept() is True


# ═══════════════════════════════════════════════════════════════
#  ProviderRouter
# ═══════════════════════════════════════════════════════════════
class TestProviderRouter:
    def test_priority_failover_selects_highest_priority(
        self, provider_configs: list[ProviderConfig]
    ) -> None:
        router = ProviderRouter(provider_configs, strategy=RoutingStrategy.PRIORITY_FAILOVER)
        selected = router.select_provider()
        assert selected is not None
        assert selected.provider_id == "alpha"  # priority=1

    def test_round_robin_rotates(
        self, provider_configs: list[ProviderConfig]
    ) -> None:
        router = ProviderRouter(provider_configs, strategy=RoutingStrategy.ROUND_ROBIN)
        ids = [router.select_provider().provider_id for _ in range(6)]  # type: ignore
        # Should cycle through all providers
        assert "alpha" in ids
        assert "beta" in ids
        assert "gamma" in ids

    def test_excludes_providers(
        self, provider_configs: list[ProviderConfig]
    ) -> None:
        router = ProviderRouter(provider_configs, strategy=RoutingStrategy.PRIORITY_FAILOVER)
        selected = router.select_provider(exclude={"alpha"})
        assert selected is not None
        assert selected.provider_id == "beta"

    def test_excludes_circuit_open(
        self, provider_configs: list[ProviderConfig]
    ) -> None:
        cb = CircuitBreaker("alpha", failure_threshold=1)
        cb.record_failure()
        router = ProviderRouter(
            provider_configs,
            strategy=RoutingStrategy.PRIORITY_FAILOVER,
            circuit_breakers={"alpha": cb},
        )
        selected = router.select_provider()
        assert selected is not None
        assert selected.provider_id == "beta"

    def test_excludes_unhealthy(
        self, provider_configs: list[ProviderConfig]
    ) -> None:
        tracker = ProviderHealthTracker("alpha", unhealthy_threshold=0.50)
        for _ in range(6):
            tracker.record_failure("err")
        for _ in range(4):
            tracker.record_success(50.0)
        router = ProviderRouter(
            provider_configs,
            strategy=RoutingStrategy.PRIORITY_FAILOVER,
            health_trackers={"alpha": tracker},
        )
        selected = router.select_provider()
        assert selected is not None
        assert selected.provider_id == "beta"

    def test_excludes_quota_exhausted(
        self, provider_configs: list[ProviderConfig]
    ) -> None:
        quota = QuotaManager("alpha", rpm_limit=1)
        quota.record_usage()
        router = ProviderRouter(
            provider_configs,
            strategy=RoutingStrategy.PRIORITY_FAILOVER,
            quota_managers={"alpha": quota},
        )
        selected = router.select_provider()
        assert selected is not None
        assert selected.provider_id == "beta"

    def test_returns_none_when_all_filtered(
        self, provider_configs: list[ProviderConfig]
    ) -> None:
        router = ProviderRouter(provider_configs, strategy=RoutingStrategy.PRIORITY_FAILOVER)
        selected = router.select_provider(exclude={"alpha", "beta", "gamma"})
        assert selected is None

    def test_excludes_providers_without_keys(self) -> None:
        configs = [
            ProviderConfig(provider_id="nokeys", api_keys=(), priority=1),
            ProviderConfig(provider_id="haskeys", api_keys=("k1",), priority=2),
        ]
        router = ProviderRouter(configs, strategy=RoutingStrategy.PRIORITY_FAILOVER)
        selected = router.select_provider()
        assert selected is not None
        assert selected.provider_id == "haskeys"

    def test_fallback_chain_ordered_by_priority(
        self, provider_configs: list[ProviderConfig]
    ) -> None:
        router = ProviderRouter(provider_configs, strategy=RoutingStrategy.PRIORITY_FAILOVER)
        chain = router.get_fallback_chain()
        assert [c.provider_id for c in chain] == ["alpha", "beta", "gamma"]

    def test_least_latency_strategy(
        self, provider_configs: list[ProviderConfig]
    ) -> None:
        trackers = {}
        for cfg in provider_configs:
            trackers[cfg.provider_id] = ProviderHealthTracker(cfg.provider_id)

        # Make gamma the fastest
        trackers["alpha"].record_success(500.0)
        trackers["beta"].record_success(300.0)
        trackers["gamma"].record_success(100.0)

        router = ProviderRouter(
            provider_configs,
            strategy=RoutingStrategy.LEAST_LATENCY,
            health_trackers=trackers,
        )
        selected = router.select_provider()
        assert selected is not None
        assert selected.provider_id == "gamma"


# ═══════════════════════════════════════════════════════════════
#  ResilientProviderGateway
# ═══════════════════════════════════════════════════════════════
class TestResilientProviderGateway:
    @pytest.mark.asyncio
    async def test_execute_success(
        self, provider_configs: list[ProviderConfig]
    ) -> None:
        gateway = ResilientProviderGateway(
            provider_configs,
            strategy=RoutingStrategy.PRIORITY_FAILOVER,
        )

        async def _fn(cfg: ProviderConfig, key: str) -> str:
            return f"ok:{cfg.provider_id}:{key}"

        result = await gateway.execute(_fn)
        assert result.startswith("ok:alpha:")

    @pytest.mark.asyncio
    async def test_failover_on_error(
        self, provider_configs: list[ProviderConfig]
    ) -> None:
        gateway = ResilientProviderGateway(
            provider_configs,
            strategy=RoutingStrategy.PRIORITY_FAILOVER,
            backoff_base=0.01,
        )

        call_count = {"alpha": 0, "beta": 0}

        async def _fn(cfg: ProviderConfig, key: str) -> str:
            call_count[cfg.provider_id] = call_count.get(cfg.provider_id, 0) + 1
            if cfg.provider_id == "alpha":
                raise ConnectionError("alpha is down")
            return f"ok:{cfg.provider_id}"

        result = await gateway.execute(_fn)
        assert result == "ok:beta"
        assert call_count["alpha"] >= 1

    @pytest.mark.asyncio
    async def test_all_providers_exhausted(
        self, provider_configs: list[ProviderConfig]
    ) -> None:
        gateway = ResilientProviderGateway(
            provider_configs,
            strategy=RoutingStrategy.PRIORITY_FAILOVER,
            backoff_base=0.01,
        )

        async def _fn(cfg: ProviderConfig, key: str) -> str:
            raise RuntimeError(f"{cfg.provider_id} failed")

        with pytest.raises(AllProvidersExhaustedError) as exc_info:
            await gateway.execute(_fn)
        assert "alpha" in exc_info.value.errors
        assert "beta" in exc_info.value.errors
        assert "gamma" in exc_info.value.errors

    @pytest.mark.asyncio
    async def test_preferred_provider(
        self, provider_configs: list[ProviderConfig]
    ) -> None:
        gateway = ResilientProviderGateway(
            provider_configs,
            strategy=RoutingStrategy.PRIORITY_FAILOVER,
        )

        async def _fn(cfg: ProviderConfig, key: str) -> str:
            return f"ok:{cfg.provider_id}"

        result = await gateway.execute(_fn, preferred_provider="gamma")
        assert result == "ok:gamma"

    @pytest.mark.asyncio
    async def test_key_rotation(
        self, provider_configs: list[ProviderConfig]
    ) -> None:
        gateway = ResilientProviderGateway(
            provider_configs,
            strategy=RoutingStrategy.PRIORITY_FAILOVER,
        )

        keys_used: list[str] = []

        async def _fn(cfg: ProviderConfig, key: str) -> str:
            keys_used.append(key)
            return "ok"

        await gateway.execute(_fn)
        await gateway.execute(_fn)
        # alpha has 2 keys, should rotate
        assert keys_used[0] == "key-a1"
        assert keys_used[1] == "key-a2"

    @pytest.mark.asyncio
    async def test_timeout_triggers_failover(
        self, provider_configs: list[ProviderConfig]
    ) -> None:
        # Override timeout to be very short
        configs = [
            ProviderConfig(
                provider_id="slow",
                api_keys=("k1",),
                priority=1,
                timeout_s=0.05,
                cb_failure_threshold=1,
            ),
            ProviderConfig(
                provider_id="fast",
                api_keys=("k2",),
                priority=2,
                timeout_s=5.0,
            ),
        ]
        gateway = ResilientProviderGateway(
            configs,
            strategy=RoutingStrategy.PRIORITY_FAILOVER,
            backoff_base=0.01,
        )

        async def _fn(cfg: ProviderConfig, key: str) -> str:
            if cfg.provider_id == "slow":
                await asyncio.sleep(1.0)
            return f"ok:{cfg.provider_id}"

        result = await gateway.execute(_fn)
        assert result == "ok:fast"

    @pytest.mark.asyncio
    async def test_health_tracking_integration(
        self, provider_configs: list[ProviderConfig]
    ) -> None:
        gateway = ResilientProviderGateway(
            provider_configs,
            strategy=RoutingStrategy.PRIORITY_FAILOVER,
        )

        async def _fn(cfg: ProviderConfig, key: str) -> str:
            return "ok"

        await gateway.execute(_fn)
        health = gateway.get_health("alpha")
        assert health is not None
        assert health.total_requests >= 1
        assert health.total_successes >= 1

    @pytest.mark.asyncio
    async def test_admin_reset(
        self, provider_configs: list[ProviderConfig]
    ) -> None:
        gateway = ResilientProviderGateway(
            provider_configs,
            strategy=RoutingStrategy.PRIORITY_FAILOVER,
            backoff_base=0.01,
        )

        # Trip alpha's circuit breaker
        async def _fail(cfg: ProviderConfig, key: str) -> str:
            if cfg.provider_id == "alpha":
                raise RuntimeError("down")
            return "ok"

        for _ in range(5):
            try:
                await gateway.execute(_fail, preferred_provider="alpha")
            except AllProvidersExhaustedError:
                pass

        # Reset alpha
        gateway.reset_provider("alpha")
        health = gateway.get_health("alpha")
        assert health is not None
        assert health.circuit_state == "closed"

    @pytest.mark.asyncio
    async def test_get_all_health(
        self, provider_configs: list[ProviderConfig]
    ) -> None:
        gateway = ResilientProviderGateway(
            provider_configs,
            strategy=RoutingStrategy.PRIORITY_FAILOVER,
        )
        healths = gateway.get_all_health()
        assert len(healths) == 3
        ids = {h.provider_id for h in healths}
        assert ids == {"alpha", "beta", "gamma"}
