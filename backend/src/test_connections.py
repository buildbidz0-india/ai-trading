import asyncio
import traceback
from sqlalchemy import text
from app.config import get_settings
from app.adapters.outbound.persistence.database import create_session_factory
from app.adapters.outbound.cache import RedisCacheAdapter

async def test_db():
    settings = get_settings()
    print(f"Testing DB: {settings.database_url}")
    try:
        factory = create_session_factory(settings)
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        print("SUCCESS: Database connected successfully")
    except Exception as e:
        print(f"FAILURE: Database connection failed")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        # traceback.print_exc()

async def test_redis():
    settings = get_settings()
    print(f"Testing Redis: {settings.redis_url}")
    try:
        cache = RedisCacheAdapter(settings.redis_url, settings.redis_max_connections)
        if await cache.health_check():
            print("SUCCESS: Redis connected successfully")
        else:
            print("FAILURE: Redis health check failed (Ping failed)")
    except Exception as e:
        print(f"FAILURE: Redis connection failed")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        # traceback.print_exc()

async def main():
    await test_db()
    print("-" * 20)
    await test_redis()

if __name__ == "__main__":
    asyncio.run(main())
