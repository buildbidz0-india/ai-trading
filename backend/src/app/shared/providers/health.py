"""Sliding-window health tracker for a single provider.

Maintains rolling success/failure counts and latency percentiles
over a configurable time window.
"""

from __future__ import annotations

import bisect
import threading
import time
from collections import deque
from dataclasses import dataclass

from app.shared.providers.types import ProviderHealth, ProviderStatus


@dataclass
class _Sample:
    timestamp: float
    success: bool
    latency_ms: float
    error: str | None = None


class ProviderHealthTracker:
    """Thread-safe, sliding-window health tracker."""

    def __init__(
        self,
        provider_id: str,
        *,
        window_seconds: float = 60.0,
        degraded_threshold: float = 0.30,
        unhealthy_threshold: float = 0.60,
    ) -> None:
        self._provider_id = provider_id
        self._window = window_seconds
        self._degraded_thr = degraded_threshold
        self._unhealthy_thr = unhealthy_threshold

        self._samples: deque[_Sample] = deque()
        self._latencies: list[float] = []  # sorted for percentile calcs
        self._lock = threading.Lock()

        # Cumulative counters (never reset)
        self._total_requests = 0
        self._total_successes = 0
        self._total_failures = 0
        self._consecutive_failures = 0
        self._last_error: str | None = None
        self._last_error_time: float | None = None

    # ── Recording ────────────────────────────────────────────
    def record_success(self, latency_ms: float) -> None:
        with self._lock:
            self._samples.append(
                _Sample(time.monotonic(), success=True, latency_ms=latency_ms)
            )
            bisect.insort(self._latencies, latency_ms)
            self._total_requests += 1
            self._total_successes += 1
            self._consecutive_failures = 0
            self._evict()

    def record_failure(self, error: str, latency_ms: float = 0.0) -> None:
        with self._lock:
            self._samples.append(
                _Sample(time.monotonic(), success=False, latency_ms=latency_ms, error=error)
            )
            if latency_ms > 0:
                bisect.insort(self._latencies, latency_ms)
            self._total_requests += 1
            self._total_failures += 1
            self._consecutive_failures += 1
            self._last_error = error
            self._last_error_time = time.monotonic()
            self._evict()

    # ── Status derivation ────────────────────────────────────
    @property
    def status(self) -> ProviderStatus:
        with self._lock:
            self._evict()
            if not self._samples:
                return ProviderStatus.HEALTHY
            failures = sum(1 for s in self._samples if not s.success)
            rate = failures / len(self._samples)
            if rate >= self._unhealthy_thr:
                return ProviderStatus.UNHEALTHY
            if rate >= self._degraded_thr:
                return ProviderStatus.DEGRADED
            return ProviderStatus.HEALTHY

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    @property
    def health(self) -> ProviderHealth:
        """Produce a read-only health snapshot."""
        with self._lock:
            self._evict()
            window_total = len(self._samples)
            window_failures = sum(1 for s in self._samples if not s.success)
            success_rate = (
                (window_total - window_failures) / window_total
                if window_total
                else 1.0
            )

        return ProviderHealth(
            provider_id=self._provider_id,
            status=self.status,
            total_requests=self._total_requests,
            total_successes=self._total_successes,
            total_failures=self._total_failures,
            consecutive_failures=self._consecutive_failures,
            success_rate=float(f"{success_rate:.4f}"),
            latency_p50_ms=self._percentile(0.50),
            latency_p95_ms=self._percentile(0.95),
            latency_p99_ms=self._percentile(0.99),
            last_error=self._last_error,
            last_error_time=self._last_error_time,
        )

    # ── Internals ────────────────────────────────────────────
    def _evict(self) -> None:
        """Remove samples outside the sliding window (caller holds lock)."""
        cutoff = time.monotonic() - self._window
        while self._samples and self._samples[0].timestamp < cutoff:
            old = self._samples.popleft()
            if old.latency_ms in self._latencies:
                self._latencies.remove(old.latency_ms)

    def _percentile(self, p: float) -> float:
        with self._lock:
            if not self._latencies:
                return 0.0
            idx = int(len(self._latencies) * p)
            idx = min(idx, len(self._latencies) - 1)
            return float(f"{self._latencies[idx]:.2f}")
