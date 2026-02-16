"""Integration tests for User Authentication, RBAC, and Token Refresh."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.config import get_settings
from app.dependencies import get_db_session
from app.adapters.outbound.persistence.models import Base

# Use in-memory SQLite for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="module")
def settings():
    return get_settings(
        database_url=TEST_DB_URL,
        jwt_secret_key="test-secret-key-must-be-very-long-to-pass-validation-checks-32-chars",
        app_env="development", # Use dev to avoid checking valid secret logic in config (though we set a valid one above)
        paper_trading_mode=True,
    )

@pytest.fixture(scope="module")
async def db_engine():
    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture(scope="module")
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, expire_on_commit=False)

@pytest.fixture
async def session(session_factory):
    async with session_factory() as session:
        yield session

@pytest.fixture
def app_with_db(settings, session_factory):
    app = create_app(settings)
    
    # Override get_db_session to use our test session
    async def override_get_db_session():
        async with session_factory() as session:
            yield session
            
    app.dependency_overrides[get_db_session] = override_get_db_session
    return app

@pytest.fixture
async def client(app_with_db):
    transport = ASGITransport(app=app_with_db)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_register_and_login_flow(client):
    # 1. Register
    reg_payload = {"username": "newtrader", "password": "securepassword123"}
    resp = await client.post("/api/v1/auth/register", json=reg_payload)
    assert resp.status_code == 201
    assert resp.json()["message"] == "User created successfully"
    
    # 2. Login
    resp = await client.post("/api/v1/auth/token", json=reg_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    
    token = data["access_token"]
    refresh = data["refresh_token"]
    
    # 3. Access Protected Route (e.g. Orders - requires auth)
    # Using existing endpoint to verify auth middleware
    # Orders might return 500 if DB not fully set for order/repo, but 401 should NOT happen
    resp = await client.get("/api/v1/orders", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code != 401 
    
    # 4. Refresh Token
    resp = await client.post(f"/api/v1/auth/refresh?refresh_token={refresh}")
    assert resp.status_code == 200
    new_data = resp.json()
    assert "access_token" in new_data
    assert new_data["access_token"] != token # Should be new token (though if content same, JWT might be same if no "iat" check? usually iat changes)
    
@pytest.mark.asyncio
async def test_rbac_enforcement(client):
    # Register/Login as Trader
    reg_payload = {"username": "regular_trader", "password": "password123"}
    await client.post("/api/v1/auth/register", json=reg_payload)
    token_resp = await client.post("/api/v1/auth/token", json=reg_payload)
    token = token_resp.json()["access_token"]
    
    # Try Admin endpoint (reset provider)
    resp = await client.post(
        "/api/v1/providers/openai/reset", 
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403
    assert "Insufficient permissions" in resp.json()["detail"]

@pytest.mark.asyncio
async def test_admin_access(client, session):
    # Manually create admin user in DB
    from app.adapters.outbound.persistence.models import UserModel
    from app.shared.security import hash_password
    
    admin_user = UserModel(
        username="admin_user",
        email="admin@example.com",
        password_hash=hash_password("adminpass"),
        role="admin",
        is_active=True
    )
    session.add(admin_user)
    await session.commit()
    
    # Login
    resp = await client.post("/api/v1/auth/token", json={"username": "admin_user", "password": "adminpass"})
    token = resp.json()["access_token"]
    
    # Try Admin endpoint
    resp = await client.post(
        "/api/v1/providers/openai/reset", 
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "reset"

@pytest.mark.asyncio
async def test_market_history_endpoint(client, session):
    # Register user
    reg_payload = {"username": "market_user", "password": "password123"}
    await client.post("/api/v1/auth/register", json=reg_payload)
    token_resp = await client.post("/api/v1/auth/token", json=reg_payload)
    token = token_resp.json()["access_token"]
    
    # Call market history (it uses Paper/Mock if no broker configured)
    resp = await client.get(
        "/api/v1/market/history",
        params={
            "symbol": "NIFTY",
            "resolution": "15",
            "from_date": "2023-01-01T09:15:00",
            "to_date": "2023-01-01T15:30:00"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "open" in data[0]
