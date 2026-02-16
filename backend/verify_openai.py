import asyncio
import os
import sys

# Add src to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from app.config import get_settings
from app.dependencies import get_llm
from app.domain.enums import LLMProvider

async def main():
    print("--- OpenAI Verification Script ---")
    
    # 1. Print Config
    settings = get_settings()
    print(f"Loaded Settings:")
    print(f"  OPENAI_API_KEY Configured: {'Yes' if settings.openai_api_key else 'No'}")
    print(f"  OPENAI_MODEL: {settings.openai_model}")
    
    if not settings.openai_api_key:
        print("ERROR: OPENAI_API_KEY is missing!")
        return

    # 2. Initialize Adapter
    print("\nInitializing LLM Adapter...")
    try:
        llm = get_llm()
        # The gateway property is available on ResilientLLMAdapter
        print(f"LLM Adapter initialized.")
        
        # 3. Invoke OpenAI
        print("\nSending request to OpenAI...")
        response = await llm.invoke(
            provider=LLMProvider.OPENAI,
            system_prompt="You are a helpful assistant.",
            user_prompt="Hello! Please reply with 'Functional', followed by the model name you are running.",
            max_tokens=50,
            temperature=0.7
        )
        
        print("\n--- Response ---")
        print(response)
        print("----------------")
        
        await llm.close()
        print("\nTest completed successfully.")
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
