"""SQLAlchemy async database session factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings


def create_engine(settings: Settings):  # type: ignore[no-untyped-def]
    url = settings.database_url
    connect_args = {}
    
    # asyncpg doesn't like 'sslmode' in the query string, it wants 'ssl' in connect_args
    if "sslmode=" in url:
        import ssl
        from sqlalchemy.engine.url import make_url
        
        parsed_url = make_url(url)
        # Strip sslmode from the URL to prevent asyncpg error
        query = dict(parsed_url.query)
        ssl_mode = query.pop("sslmode", "require")
        url = str(parsed_url.set(query=query))
        
        # For Neon/Azure/RDS, setting ssl context or just ssl=True is common
        if ssl_mode in ("require", "verify-full", "verify-ca"):
            # Create a default SSL context that trusts system CA
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE  # Common for Neon pooler
            connect_args["ssl"] = ctx

    return create_async_engine(
        url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        echo=settings.app_debug,
        pool_pre_ping=True,
        connect_args=connect_args
    )


def create_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    engine = create_engine(settings)
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
