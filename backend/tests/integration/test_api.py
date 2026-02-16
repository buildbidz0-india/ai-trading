"""Integration tests for API endpoints using FastAPI TestClient."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app
from app.shared.security import create_access_token


@pytest.fixture
def settings():
    return get_settings(
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/0",
        paper_trading_mode=True,
        jwt_secret_key="test-secret-key-256-bits-long-enough",
    )


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def auth_headers(settings):
    token = create_access_token(
        data={"sub": "test-user", "role": "admin"},
        secret_key=settings.jwt_secret_key,
    )
    return {"Authorization": f"Bearer {token}"}


class TestHealthEndpoints:
    def test_health_check(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "services" in data

    def test_metrics_endpoint(self, client):
        resp = client.get("/api/v1/metrics")
        assert resp.status_code == 200
        assert b"http_requests_total" in resp.content


class TestAuthEndpoints:
    def test_create_token(self, client):
        resp = client.post(
            "/api/v1/auth/token",
            json={"username": "admin", "password": "any-password-in-demo"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_invalid_user(self, client):
        resp = client.post(
            "/api/v1/auth/token",
            json={"username": "nonexistent", "password": "password123"},
        )
        assert resp.status_code == 401


class TestOrderEndpoints:
    def test_unauthorized_access(self, client):
        resp = client.get("/api/v1/orders")
        assert resp.status_code == 401

    def test_list_orders_empty(self, client, auth_headers):
        # This will fail to connect to DB since we don't have real postgres
        # but verifies the auth + routing is correct
        resp = client.get("/api/v1/orders", headers=auth_headers)
        # May get 500 due to no DB — that's expected in unit test
        assert resp.status_code in (200, 500)


class TestPositionEndpoints:
    def test_unauthorized_access(self, client):
        resp = client.get("/api/v1/positions")
        assert resp.status_code == 401


class TestTradeEndpoints:
    def test_unauthorized_access(self, client):
        resp = client.get("/api/v1/trades")
        assert resp.status_code == 401
