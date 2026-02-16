import asyncio
import sys
import os

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), "backend", "src"))

async def verify():
    print("Verifying provider framework imports...")
    try:
        from app.shared.providers.gateway import ResilientProviderGateway
        from app.shared.providers.types import ProviderConfig, RoutingStrategy
        from app.shared.providers.circuit_breaker import CircuitBreaker
        from app.shared.providers.health import ProviderHealthTracker
        from app.shared.providers.quota import QuotaManager
        
        print("✅ All imports successful.")
        
        # Basic instantiation test
        config = ProviderConfig(
            provider_id="test-provider",
            api_keys=["key1"],
            priority=1
        )
        gateway = ResilientProviderGateway(providers=[config])
        print("✅ Gateway instantiation successful.")
        
        # Test health tracking (verify no round() errors)
        tracker = ProviderHealthTracker("test-provider")
        tracker.record_success(100.0)
        health = tracker.health
        print(f"✅ Health snapshot successful: rate={health.success_rate}")
        
        # Test quota (verify no round() errors)
        quota = QuotaManager("test-provider", rpm_limit=60)
        quota.record_usage(10)
        rem = quota.remaining_pct
        print(f"✅ Quota remaining successful: {rem}%")
        
        # Test circuit breaker (verify no round() errors)
        cb = CircuitBreaker("test-provider", cooldown_seconds=0)
        cb.record_failure()
        cb.record_failure() # Need more failures if threshold > 2, but we just check if it runs
        print("✅ Circuit breaker record successful.")
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(verify())
