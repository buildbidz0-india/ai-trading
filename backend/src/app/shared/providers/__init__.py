"""Multi-provider resilience framework.

Provides rotation, failover, circuit breaking, quota management,
and health tracking for any outbound API provider.
"""

from app.shared.providers.types import (
    ProviderConfig,
    ProviderHealth,
    ProviderStatus,
    RoutingStrategy,
)
from app.shared.providers.health import ProviderHealthTracker
from app.shared.providers.circuit_breaker import CircuitBreaker
from app.shared.providers.quota import QuotaManager
from app.shared.providers.router import ProviderRouter
from app.shared.providers.gateway import ResilientProviderGateway

__all__ = [
    "CircuitBreaker",
    "ProviderConfig",
    "ProviderHealth",
    "ProviderHealthTracker",
    "ProviderRouter",
    "ProviderStatus",
    "QuotaManager",
    "ResilientProviderGateway",
    "RoutingStrategy",
]
