
import asyncio
import os
import structlog
from app.adapters.outbound.llm import ResilientLLMAdapter, build_provider_configs
from app.shared.providers.types import ProviderConfig

# Configure structured logging
structlog.configure(
    processors=[structlog.processors.JSONRenderer()]
)

async def main():
    print("Locked & Loaded: Testing Key Rotation & Gemini 3 Pro")

    # Mock keys logic
    # In reality, this would pull from .env, but for a test script we can simulate
    # passing distinct keys to verify rotation logic.
    keys = ["key-1", "key-2", "key-3"]
    
    # We'll use a mock "invoke" approach or just verify the gateway internals
    # since we don't have real valid keys for all of them to make live calls.
    # However, we CAN test the rotation logic in isolation.
    
    configs = build_provider_configs(
        google_api_keys=",".join(keys),
        google_model="gemini-3-pro",
        priority_order="google"
    )
    
    adapter = ResilientLLMAdapter(configs)
    gateway = adapter.gateway
    
    print(f"Provider Configs: {[p.provider_id for p in configs]}")
    google_config = next(c for c in configs if c.provider_id == "google")
    print(f"Google Keys Configured: {len(google_config.api_keys)}")
    print(f"Google Model Metadata: {google_config.metadata}")
    
    # Verify KeyManager initialization
    km = gateway._key_managers["google"]
    print(f"KeyManager initialized with {km.key_count} keys")
    
    # Simulate requests and check key rotation
    # We can't easily mock the internal _try_provider without patching,
    # but we can check the KeyManager directly.
    
    print("\n--- Testing Rotation ---")
    for i in range(5):
        key_state = km.select_key()
        print(f"Request {i+1}: Selected Key Index {key_state.index} ({key_state.api_key})")
        # Simulate success
        km.record_success(key_state.index, latency_ms=100, tokens=10)
        
    print("\n--- Testing Failure/Circuit Break ---")
    # Fail key-0 multiple times
    key_state = km._keys[0] # Grab first key
    print(f"Failing Key 0 ({key_state.api_key}) until circuit break...")
    
    for _ in range(6): # Threshold is 5
        km.record_failure(0, "Mock Error")
        
    print(f"Key 0 Circuit State: {key_state.circuit_breaker.state}")
    
    # Next selection should skip key 0
    next_key = km.select_key()
    print(f"Next selected key index: {next_key.index} (Should not be 0)")
    
    print("\nTest Complete.")

if __name__ == "__main__":
    asyncio.run(main())
