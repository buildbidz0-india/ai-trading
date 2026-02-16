"""Unit tests for application query handlers."""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from app.application.queries import (
    GetPositionsQuery,
    GetPositionsHandler,
    GetOrdersQuery,
    GetOrdersHandler,
)
from app.domain.entities import Order, Position
from app.domain.enums import OrderStatus, Side, Exchange, ProductType, OrderType
from app.domain.value_objects import Symbol, Quantity, Money


@pytest.fixture
def mock_position_repo():
    repo = Mock()
    repo.list_open = AsyncMock(return_value=[])
    repo.list_all = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_order_repo():
    repo = Mock()
    repo.list_by_status = AsyncMock(return_value=[])
    repo.list_recent = AsyncMock(return_value=[])
    return repo


@pytest.mark.asyncio
async def test_get_positions_open_only(mock_position_repo):
    handler = GetPositionsHandler(position_repo=mock_position_repo)
    query = GetPositionsQuery(open_only=True)

    result = await handler.handle(query)

    assert result == []
    mock_position_repo.list_open.assert_called_once()
    mock_position_repo.list_all.assert_not_called()


@pytest.mark.asyncio
async def test_get_positions_all(mock_position_repo):
    handler = GetPositionsHandler(position_repo=mock_position_repo)
    query = GetPositionsQuery(open_only=False)

    result = await handler.handle(query)

    assert result == []
    mock_position_repo.list_all.assert_called_once()
    mock_position_repo.list_open.assert_not_called()


@pytest.mark.asyncio
async def test_get_orders_by_status(mock_order_repo):
    handler = GetOrdersHandler(order_repo=mock_order_repo)
    query = GetOrdersQuery(status=OrderStatus.FILLED)

    result = await handler.handle(query)

    assert result == []
    mock_order_repo.list_by_status.assert_called_once_with(OrderStatus.FILLED, limit=100)


@pytest.mark.asyncio
async def test_get_orders_recent(mock_order_repo):
    handler = GetOrdersHandler(order_repo=mock_order_repo)
    query = GetOrdersQuery(status=None, limit=50)

    result = await handler.handle(query)

    assert result == []
    mock_order_repo.list_recent.assert_called_once_with(since=None, limit=50)
