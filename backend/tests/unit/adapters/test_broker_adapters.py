"""Unit tests for production broker adapters.

Tests use mocked httpx responses to verify API mapping, error handling,
and correct BrokerPort implementation without hitting real APIs.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.adapters.outbound.broker.dhan import DhanBrokerAdapter
from app.adapters.outbound.broker.zerodha import ZerodhaBrokerAdapter
from app.adapters.outbound.broker.shoonya import ShoonyaBrokerAdapter
from app.domain.entities import Order
from app.domain.enums import Exchange, OrderSide, OrderType, ProductType
from app.domain.value_objects import Money, Quantity, Symbol


@pytest.fixture
def sample_order() -> Order:
    return Order(
        id="test-001",
        symbol=Symbol("NIFTY"),
        exchange=Exchange.NFO,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        product_type=ProductType.NRML,
        quantity=Quantity(50, lot_size=50),
        price=Money(Decimal("150.00")),
    )


# ═══════════════════════════════════════════════════════════════
#  Dhan Adapter Tests
# ═══════════════════════════════════════════════════════════════
class TestDhanBrokerAdapter:
    @pytest.fixture
    def adapter(self):
        return DhanBrokerAdapter(client_id="test-client", access_token="test-token")

    @pytest.mark.asyncio
    async def test_place_order(self, adapter, sample_order):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"orderId": "DHAN-12345"}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(adapter._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            broker_id = await adapter.place_order(sample_order)
            assert broker_id == "DHAN-12345"

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, adapter):
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch.object(adapter._client, "delete", new_callable=AsyncMock, return_value=mock_resp):
            result = await adapter.cancel_order("DHAN-12345")
            assert result is True

    @pytest.mark.asyncio
    async def test_cancel_order_failure(self, adapter):
        mock_resp = MagicMock()
        mock_resp.status_code = 400

        with patch.object(adapter._client, "delete", new_callable=AsyncMock, return_value=mock_resp):
            result = await adapter.cancel_order("DHAN-99999")
            assert result is False

    @pytest.mark.asyncio
    async def test_get_positions(self, adapter):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": [{"symbol": "NIFTY", "qty": 50}]}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(adapter._client, "get", new_callable=AsyncMock, return_value=mock_resp):
            positions = await adapter.get_positions()
            assert len(positions) == 1

    @pytest.mark.asyncio
    async def test_get_order_status(self, adapter):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"orderId": "DHAN-12345", "status": "FILLED"}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(adapter._client, "get", new_callable=AsyncMock, return_value=mock_resp):
            status = await adapter.get_order_status("DHAN-12345")
            assert status["status"] == "FILLED"

    def test_exchange_mapping(self, adapter):
        assert adapter._EXCHANGE_MAP["NFO"] == "NSE_FNO"
        assert adapter._EXCHANGE_MAP["NSE"] == "NSE_EQ"
        assert adapter._EXCHANGE_MAP["MCX"] == "MCX_COMM"

    def test_order_type_mapping(self, adapter):
        assert adapter._ORDER_TYPE_MAP["STOP_LOSS"] == "STOP_LOSS_MARKET"


# ═══════════════════════════════════════════════════════════════
#  Zerodha Adapter Tests
# ═══════════════════════════════════════════════════════════════
class TestZerodhaBrokerAdapter:
    @pytest.fixture
    def adapter(self):
        return ZerodhaBrokerAdapter(
            api_key="test-key", api_secret="test-secret", access_token="test-token"
        )

    @pytest.mark.asyncio
    async def test_place_order(self, adapter, sample_order):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"order_id": "KITE-67890"}}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(adapter._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            broker_id = await adapter.place_order(sample_order)
            assert broker_id == "KITE-67890"

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, adapter):
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch.object(adapter._client, "delete", new_callable=AsyncMock, return_value=mock_resp):
            result = await adapter.cancel_order("KITE-67890")
            assert result is True

    @pytest.mark.asyncio
    async def test_get_positions(self, adapter):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"net": [{"symbol": "NIFTY", "quantity": 50}]}}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(adapter._client, "get", new_callable=AsyncMock, return_value=mock_resp):
            positions = await adapter.get_positions()
            assert len(positions) == 1

    def test_set_access_token(self, adapter):
        adapter.set_access_token("new-token")
        assert adapter._access_token == "new-token"

    def test_order_type_mapping(self, adapter):
        assert adapter._ORDER_TYPE_MAP["STOP_LOSS"] == "SL-M"
        assert adapter._ORDER_TYPE_MAP["STOP_LOSS_LIMIT"] == "SL"


# ═══════════════════════════════════════════════════════════════
#  Shoonya Adapter Tests
# ═══════════════════════════════════════════════════════════════
class TestShoonyaBrokerAdapter:
    @pytest.fixture
    def adapter(self):
        return ShoonyaBrokerAdapter(
            user_id="test-user", password="test-pass", api_key="test-api-key"
        )

    @pytest.mark.asyncio
    async def test_login(self, adapter):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"susertoken": "session-abc123"}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(adapter._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            token = await adapter.login()
            assert token == "session-abc123"
            assert adapter._session_token == "session-abc123"

    @pytest.mark.asyncio
    async def test_place_order(self, adapter, sample_order):
        adapter._session_token = "test-session"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"norenordno": "SHNY-11111"}
        mock_resp.raise_for_status = MagicMock()

        with patch.object(adapter._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            broker_id = await adapter.place_order(sample_order)
            assert broker_id == "SHNY-11111"

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, adapter):
        adapter._session_token = "test-session"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"stat": "Ok"}

        with patch.object(adapter._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            result = await adapter.cancel_order("SHNY-11111")
            assert result is True

    @pytest.mark.asyncio
    async def test_cancel_order_failure(self, adapter):
        adapter._session_token = "test-session"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"stat": "Not_OK", "emsg": "Order not found"}

        with patch.object(adapter._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            result = await adapter.cancel_order("SHNY-99999")
            assert result is False

    @pytest.mark.asyncio
    async def test_get_positions(self, adapter):
        adapter._session_token = "test-session"
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"symbol": "NIFTY", "netqty": "50"}]
        mock_resp.raise_for_status = MagicMock()

        with patch.object(adapter._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            positions = await adapter.get_positions()
            assert len(positions) == 1

    def test_side_mapping(self, adapter):
        assert adapter._SIDE_MAP["BUY"] == "B"
        assert adapter._SIDE_MAP["SELL"] == "S"

    def test_product_mapping(self, adapter):
        assert adapter._PRODUCT_MAP["CNC"] == "C"
        assert adapter._PRODUCT_MAP["MIS"] == "I"
        assert adapter._PRODUCT_MAP["NRML"] == "M"
