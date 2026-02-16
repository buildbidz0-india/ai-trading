"""Initial schema — orders, trades, positions, instruments.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-02-16
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Orders ────────────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("instrument_id", sa.String(32), nullable=True),
        sa.Column("symbol", sa.String(30), nullable=False, index=True),
        sa.Column("exchange", sa.String(10), nullable=False),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("order_type", sa.String(20), nullable=False),
        sa.Column("product_type", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("lot_size", sa.Integer, server_default="1"),
        sa.Column("price", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("trigger_price", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("status", sa.String(25), nullable=False, index=True, server_default="PENDING_VALIDATION"),
        sa.Column("broker_order_id", sa.String(64), nullable=True),
        sa.Column("idempotency_key", sa.String(32), unique=True, nullable=False),
        sa.Column("source", sa.String(20), server_default="SYSTEM"),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_orders_created", "orders", ["created_at"])
    op.create_index("ix_orders_symbol_status", "orders", ["symbol", "status"])

    # ── Trades ────────────────────────────────────────────────
    op.create_table(
        "trades",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("order_id", sa.String(32), nullable=False, index=True),
        sa.Column("instrument_id", sa.String(32), nullable=True),
        sa.Column("symbol", sa.String(30), nullable=False, index=True),
        sa.Column("exchange", sa.String(10), nullable=False),
        sa.Column("side", sa.String(4), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("lot_size", sa.Integer, server_default="1"),
        sa.Column("price", sa.Numeric(14, 4), nullable=False),
        sa.Column("fees", sa.Numeric(14, 4), server_default="0"),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_trades_executed", "trades", ["executed_at"])

    # ── Positions ─────────────────────────────────────────────
    op.create_table(
        "positions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("instrument_id", sa.String(32), nullable=False, unique=True),
        sa.Column("symbol", sa.String(30), nullable=False, index=True),
        sa.Column("exchange", sa.String(10), nullable=False),
        sa.Column("net_quantity", sa.Integer, server_default="0"),
        sa.Column("average_price", sa.Numeric(14, 4), server_default="0"),
        sa.Column("realised_pnl", sa.Numeric(14, 4), server_default="0"),
        sa.Column("unrealised_pnl", sa.Numeric(14, 4), server_default="0"),
        sa.Column("delta", sa.Numeric(10, 6), server_default="0"),
        sa.Column("gamma", sa.Numeric(10, 6), server_default="0"),
        sa.Column("theta", sa.Numeric(10, 6), server_default="0"),
        sa.Column("vega", sa.Numeric(10, 6), server_default="0"),
        sa.Column("rho", sa.Numeric(10, 6), server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Instruments ───────────────────────────────────────────
    op.create_table(
        "instruments",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("symbol", sa.String(30), nullable=False, index=True),
        sa.Column("exchange", sa.String(10), nullable=False),
        sa.Column("instrument_type", sa.String(15), nullable=False),
        sa.Column("lot_size", sa.Integer, server_default="1"),
        sa.Column("tick_size", sa.Numeric(10, 4), server_default="0.05"),
        sa.Column("option_type", sa.String(2), nullable=True),
        sa.Column("strike_price", sa.Numeric(14, 4), nullable=True),
        sa.Column("expiry", sa.DateTime, nullable=True),
    )
    op.create_index("ix_instruments_symbol_exchange", "instruments", ["symbol", "exchange"])


def downgrade() -> None:
    op.drop_table("instruments")
    op.drop_table("positions")
    op.drop_table("trades")
    op.drop_table("orders")
