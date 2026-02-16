"""Circuit breaker — prevents cascading failures by isolating unhealthy providers.

State machine:
    CLOSED  → (N consecutive failures) → OPEN
    OPEN    → (cooldown expires)       → HALF_OPEN
    HALF_OPEN → (probe succeeds)       → CLOSED
    HALF_OPEN → (probe fails)          → OPEN
"""

from __future__ import annotations

import enum
import time
import threading

import structlog

logger = structlog.get_logger(__name__)


class CircuitState(str, enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Per-provider circuit breaker with automatic half-open probing."""

    def __init__(
        self,
        provider_id: str,
        *,
        failure_threshold: int = 5,
        cooldown_seconds: float = 30.0,
    ) -> None:
        self._provider_id = provider_id
        self._failure_threshold = failure_threshold
        self._cooldown = cooldown_seconds

        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._last_failure_time: float = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._maybe_transition_to_half_open()
            return self._state

    def can_execute(self) -> bool:
        """Check if the circuit allows a request through."""
        with self._lock:
            self._maybe_transition_to_half_open()

            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.HALF_OPEN:
                # Allow exactly one probe request
                return True

            # OPEN — no requests allowed
            return False

    def record_success(self) -> None:
        """Record a successful call — resets the circuit."""
        with self._lock:
            prev = self._state
            self._state = CircuitState.CLOSED
            self._consecutive_failures = 0
            if prev != CircuitState.CLOSED:
                logger.info(
                    "circuit_breaker_closed",
                    provider=self._provider_id,
                    previous_state=prev.value,
                )

    def record_failure(self) -> None:
        """Record a failed call — may trip the circuit."""
        with self._lock:
            self._consecutive_failures += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                # Probe failed — go back to OPEN
                self._state = CircuitState.OPEN
                logger.warning(
                    "circuit_breaker_reopened",
                    provider=self._provider_id,
                    failures=self._consecutive_failures,
                )
            elif (
                self._state == CircuitState.CLOSED
                and self._consecutive_failures >= self._failure_threshold
            ):
                self._state = CircuitState.OPEN
                logger.warning(
                    "circuit_breaker_opened",
                    provider=self._provider_id,
                    failures=self._consecutive_failures,
                    cooldown_s=self._cooldown,
                )

    def reset(self) -> None:
        """Force-reset the circuit to CLOSED (for admin override)."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._consecutive_failures = 0
            logger.info("circuit_breaker_force_reset", provider=self._provider_id)

    def _maybe_transition_to_half_open(self) -> None:
        """Caller must hold lock."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self._cooldown:
                self._state = CircuitState.HALF_OPEN
                logger.info(
                    "circuit_breaker_half_open",
                    provider=self._provider_id,
                    elapsed_s=round(elapsed, 1),
                )
