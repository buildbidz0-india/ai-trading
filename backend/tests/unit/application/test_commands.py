"""Unit tests for application command handlers."""

import pytest
from unittest.mock import AsyncMock, Mock, ANY
from decimal import Decimal
import uuid

from app.application.commands import (
    PlaceOrderCommand,
    PlaceOrderHandler,
    CancelOrderCommand,
    CancelOrderHandler,
)
from app.domain.entities import Order, Position
from app.domain.enums import OrderType, Side, Exchange, ProductType, OrderStatus
from app.domain.value_objects import Money, Quantity, Symbol
from app.domain.exceptions import RiskLimitExceededError


@pytest.fixture
def mock_order_repo():
    repo = Mock()
    repo.save = AsyncMock()
    repo.get = AsyncMock()
    return repo


@pytest.fixture
def mock_position_repo():
    repo = Mock()
    repo.list_open = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_broker():
    broker = Mock()
    broker.place_order = AsyncMock(return_value="BROKER-123")
    broker.cancel_order = AsyncMock(return_value=True)
    return broker


@pytest.fixture
def mock_cache():
    cache = Mock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    return cache


@pytest.fixture
def mock_event_bus():
    bus = Mock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def mock_risk_engine():
    engine = Mock()
    engine.check = Mock(return_value=None)  # Does not raise
    return engine


@pytest.fixture
def mock_guardrails():
    rails = Mock()
    rails.validate = AsyncMock(return_value=None)
    return rails


@pytest.mark.asyncio
async def test_place_order_handler_success(
    mock_order_repo,
    mock_position_repo,
    mock_broker,
    mock_cache,
    mock_event_bus,
    mock_risk_engine,
    mock_guardrails,
):
    handler = PlaceOrderHandler(
        order_repo=mock_order_repo,
        position_repo=mock_position_repo,
        broker=mock_broker,
        cache=mock_cache,
        event_bus=mock_event_bus,
        risk_engine=mock_risk_engine,
        guardrails=mock_guardrails,
        paper_mode=False,
    )

    cmd = PlaceOrderCommand(
        symbol="TCS",
        exchange="NSE",
        side="BUY",
        order_type="MARKET",
        product_type="MIS",
        quantity=10,
        price="3500.00",
        source="TEST",
    )

    order_id = await handler.handle(cmd)

    # Verify dependencies called
    mock_guardrails.validate.assert_called_once()
    mock_position_repo.list_open.assert_called_once()
    mock_risk_engine.check.assert_called_once()
    mock_order_repo.save.assert_called()  # Saved PENDING and PLACED
    mock_broker.place_order.assert_called_once()
    mock_event_bus.publish.assert_called()
    assert order_id is not None


@pytest.mark.asyncio
async def test_place_order_risk_rejection(
    mock_order_repo,
    mock_position_repo,
    mock_broker,
    mock_cache,
    mock_event_bus,
    mock_risk_engine,
    mock_guardrails,
):
    mock_risk_engine.check.side_effect = RiskLimitExceededError("Too much risk")

    handler = PlaceOrderHandler(
        order_repo=mock_order_repo,
        position_repo=mock_position_repo,
        broker=mock_broker,
        cache=mock_cache,
        event_bus=mock_event_bus,
        risk_engine=mock_risk_engine,
        guardrails=mock_guardrails,
    )

    cmd = PlaceOrderCommand(
        symbol="TCS",
        exchange="NSE",
        side="BUY",
        order_type="MARKET",
        product_type="MIS",
        quantity=10000,
        price="3500.00",
    )

    with pytest.raises(RiskLimitExceededError):
        await handler.handle(cmd)

    mock_broker.place_order.assert_not_called()
    mock_order_repo.save.assert_not_called()  # Should reject before saving initial PENDING


@pytest.mark.asyncio
async def test_cancel_order_handler_success(
    mock_order_repo, mock_broker, mock_event_bus
):
    handler = CancelOrderHandler(
        order_repo=mock_order_repo,
        broker=mock_broker,
        event_bus=mock_event_bus,
    )

    # Setup existing order
    order_id = uuid.uuid4()
    existing_order = Order.create(
        symbol=Symbol("TCS"),
        exchange=Exchange.NSE,
        side=Side.BUY,
        order_type=OrderType.MARKET,
        product_type=ProductType.MIS,
        quantity=Quantity(10),
        price=Money("3500"),
    )
    # Simulate placed state
    existing_order._status = OrderStatus.PLACED
    existing_order._broker_order_id = "BROKER-123"
    
    mock_order_repo.get.return_value = existing_order

    cmd = CancelOrderCommand(order_id=str(existing_order.id))
    success = await handler.handle(cmd)

    assert success is True
    mock_broker.cancel_order.assert_called_with("BROKER-123")
    mock_order_repo.save.assert_called_once()  # Saved CANCELLED state
