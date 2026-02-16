"""Quota manager — tracks RPM and TPM budgets per provider.

Uses a sliding-window approach: requests older than the window are
automatically evicted, so the budget self-replenishes over time.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class _UsageRecord:
    timestamp: float
    tokens: int


class QuotaManager:
    """Per-provider sliding-window quota tracker (RPM + TPM)."""

    def __init__(
        self,
        provider_id: str,
        *,
        rpm_limit: int = 60,
        tpm_limit: int = 0,
        window_seconds: float = 60.0,
        warning_threshold: float = 0.90,
    ) -> None:
        self._provider_id = provider_id
        self._rpm_limit = rpm_limit
        self._tpm_limit = tpm_limit
        self._window = window_seconds
        self._warning_thr = warning_threshold

        self._records: deque[_UsageRecord] = deque()
        self._lock = threading.Lock()
        self._warning_emitted = False

    def can_accept(self, estimated_tokens: int = 0) -> bool:
        """Check if the provider can accept a new request."""
        with self._lock:
            self._evict()

            # RPM check
            if self._rpm_limit > 0 and len(self._records) >= self._rpm_limit:
                logger.debug(
                    "quota_rpm_exhausted",
                    provider=self._provider_id,
                    current=len(self._records),
                    limit=self._rpm_limit,
                )
                return False

            # TPM check
            if self._tpm_limit > 0:
                used_tokens = sum(r.tokens for r in self._records)
                if used_tokens + estimated_tokens > self._tpm_limit:
                    logger.debug(
                        "quota_tpm_exhausted",
                        provider=self._provider_id,
                        used=used_tokens,
                        estimated=estimated_tokens,
                        limit=self._tpm_limit,
                    )
                    return False

            return True

    def record_usage(self, tokens: int = 0) -> None:
        """Record a request + token usage."""
        with self._lock:
            self._records.append(_UsageRecord(time.monotonic(), tokens))
            self._evict()
            self._check_warning()

    @property
    def remaining_pct(self) -> float:
        """Percentage of quota remaining (based on RPM)."""
        with self._lock:
            self._evict()
            if self._rpm_limit <= 0:
                return 100.0
            used = len(self._records)
            return float(f"{(max(0.0, (1.0 - used / self._rpm_limit)) * 100):.1f}")

    @property
    def requests_in_window(self) -> int:
        with self._lock:
            self._evict()
            return len(self._records)

    @property
    def tokens_in_window(self) -> int:
        with self._lock:
            self._evict()
            return sum(r.tokens for r in self._records)

    def reset(self) -> None:
        """Force-reset all counters (for admin override)."""
        with self._lock:
            self._records.clear()
            self._warning_emitted = False

    # ── Internals ────────────────────────────────────────────
    def _evict(self) -> None:
        """Remove records outside the sliding window. Caller holds lock."""
        cutoff = time.monotonic() - self._window
        while self._records and self._records[0].timestamp < cutoff:
            self._records.popleft()
        # Reset warning flag when usage drops
        if self._rpm_limit > 0 and len(self._records) / self._rpm_limit < self._warning_thr:
            self._warning_emitted = False

    def _check_warning(self) -> None:
        """Emit early warning when approaching limit. Caller holds lock."""
        if self._rpm_limit <= 0 or self._warning_emitted:
            return
        usage_pct = len(self._records) / self._rpm_limit
        if usage_pct >= self._warning_thr:
            self._warning_emitted = True
            logger.warning(
                "quota_warning",
                provider=self._provider_id,
                usage_pct=float(f"{(usage_pct * 100):.1f}"),
                requests_used=len(self._records),
                rpm_limit=self._rpm_limit,
            )
