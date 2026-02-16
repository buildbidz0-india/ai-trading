import asyncio
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
        print("✅ Database connected successfully")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

async def test_redis():
    settings = get_settings()
    print(f"Testing Redis: {settings.redis_url}")
    try:
        cache = RedisCacheAdapter(settings.redis_url, settings.redis_max_connections)
        if await cache.health_check():
            print("✅ Redis connected successfully")
        else:
            print("❌ Redis health check failed (Ping failed)")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")

async def main():
    await test_db()
    print("-" * 20)
    await test_redis()

if __name__ == "__main__":
    asyncio.run(main())
