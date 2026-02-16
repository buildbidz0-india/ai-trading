"""Key manager - handles rotation, health, and limiting for individual API keys.

Each key has its own:
- CircuitBreaker: to isolate keys that are temporarily invalid or rate-limited.
- QuotaManager: to track usage against limits.
- HealthTracker: to track latency and success rates.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Sequence

import structlog

from app.shared.providers.circuit_breaker import CircuitBreaker
from app.shared.providers.types import ProviderConfig
from app.shared.providers.quota import QuotaManager
from app.shared.providers.health import ProviderHealthTracker

logger = structlog.get_logger(__name__)


@dataclass
class KeyState:
    """State for a single API key."""
    api_key: str
    index: int
    circuit_breaker: CircuitBreaker
    quota_manager: QuotaManager
    health_tracker: ProviderHealthTracker

    @property
    def is_usable(self) -> bool:
        """Check if key is healthy and has quota."""
        if not self.circuit_breaker.can_execute():
            return False
        # We don't check quota here for "usability" in strict sense, 
        # but the manager will filter based on quota capacity for the specific request.
        return True


class KeyManager:
    """Manages a pool of API keys for a single provider."""

    def __init__(self, config: ProviderConfig) -> None:
        self.provider_id = config.provider_id
        self._config = config
        self._keys: list[KeyState] = []
        self._lock = threading.Lock()
        self._rr_index = 0

        # Initialize state for each key
        for idx, key in enumerate(config.api_keys):
            # Create isolated components for each key
            # We assume config limits are PER KEY if they are being rotated, 
            # or split? Usually with rotation, you want to use the full limit of each key.
            # If the provider config implies "total provider limit", we might need a global limiter too.
            # For now, we assume limits are per-key (standard for multi-key setups).
            
            self._keys.append(KeyState(
                api_key=key,
                index=idx,
                circuit_breaker=CircuitBreaker(
                    provider_id=f"{self.provider_id}:key-{idx}",
                    failure_threshold=config.cb_failure_threshold,
                    cooldown_seconds=config.cb_cooldown_s,
                ),
                quota_manager=QuotaManager(
                    provider_id=f"{self.provider_id}:key-{idx}",
                    rpm_limit=config.rpm_limit,
                    tpm_limit=config.tpm_limit,
                ),
                health_tracker=ProviderHealthTracker(
                    provider_id=f"{self.provider_id}:key-{idx}",
                    window_seconds=60.0, # Default window
                )
            ))

    def get_exhausted_errors(self) -> list[str]:
        """Return a summary of why keys are unavailable."""
        errors = []
        for ks in self._keys:
            if not ks.circuit_breaker.can_execute():
                errors.append(f"Key {ks.index}: Circuit Open")
            elif not ks.quota_manager.can_accept(0): # Check if even 0 tokens would pass (basic quota check)
                errors.append(f"Key {ks.index}: Quota Exhausted")
        return errors

    def select_key(self, estimated_tokens: int = 0) -> KeyState | None:
        """Get the next available key using round-robin."""
        with self._lock:
            start_index = self._rr_index
            count = len(self._keys)
            
            if count == 0:
                return None

            for i in range(count):
                idx = (start_index + i) % count
                ks = self._keys[idx]

                # 1. Check Circuit Breaker
                if not ks.circuit_breaker.can_execute():
                    continue

                # 2. Check Quota
                if not ks.quota_manager.can_accept(estimated_tokens):
                    continue

                # Found a valid key
                self._rr_index = (idx + 1) % count
                return ks
            
            return None

    def record_success(self, key_index: int, latency_ms: float, tokens: int) -> None:
        """Record success for a specific key."""
        if 0 <= key_index < len(self._keys):
            ks = self._keys[key_index]
            ks.circuit_breaker.record_success()
            ks.quota_manager.record_usage(tokens)
            ks.health_tracker.record_success(latency_ms)

    def record_failure(self, key_index: int, error: str, latency_ms: float = 0.0) -> None:
        """Record failure for a specific key."""
        if 0 <= key_index < len(self._keys):
            ks = self._keys[key_index]
            ks.circuit_breaker.record_failure()
            ks.health_tracker.record_failure(error, latency_ms)

    @property
    def any_healthy(self) -> bool:
        """Check if at least one key is theoretically usable (ignoring strict quota for now)."""
        return any(ks.circuit_breaker.can_execute() for ks in self._keys)

    @property
    def key_count(self) -> int:
        return len(self._keys)
