
import asyncio
import os
import sys
# Mock environment for testing
os.environ["OPENAI_API_KEY"] = "986ee665-9e10-43cf-b1c1-4fbfa2c573e7/zainimam841438/deploy-model-project"
os.environ["OPENAI_BASE_URL"] = "https://lightning.ai/api/v1"
os.environ["OPENAI_MODEL"] = "anthropic/claude-opus-4-6" 
# Ensure we can import app
sys.path.append(os.path.join(os.getcwd(), 'backend', 'src'))

from app.adapters.outbound.llm import ResilientLLMAdapter, build_provider_configs
from app.shared.providers.types import RoutingStrategy

async def main():
    print("Setting up ResilientLLMAdapter with Lightning AI config...")
    
    provider_configs = build_provider_configs(
        openai_api_key=os.environ["OPENAI_API_KEY"],
        openai_base_url=os.environ["OPENAI_BASE_URL"],
        openai_model=os.environ["OPENAI_MODEL"],
        priority_order="openai", # Prioritize OpenAI for this test
    )

    adapter = ResilientLLMAdapter(
        provider_configs,
        routing_strategy=RoutingStrategy.PRIORITY_FAILOVER,
    )

    print(f"Invoking LLM via adapter (Model: {os.environ['OPENAI_MODEL']})...")
    try:
        response = await adapter._invoke_openai(
            api_key=os.environ["OPENAI_API_KEY"],
            system_prompt="You are a helpful assistant.",
            user_prompt="Hello from the integration test!",
            temperature=0.7,
            max_tokens=100,
            model=os.environ["OPENAI_MODEL"]
        )
        print("\n--- Response ---")
        print(response)
        print("----------------")
    except Exception as e:
        print(f"\nERROR: {e}")
    finally:
        await adapter.close()

if __name__ == "__main__":
    asyncio.run(main())
