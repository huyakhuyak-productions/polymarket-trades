from __future__ import annotations

import pytest

from polymarket_trades.application.container import build_container, close_container
from polymarket_trades.domain.value_objects.trade_mode import TradeMode
from polymarket_trades.infrastructure.config.settings import Settings


class TestContainer:
    @pytest.mark.asyncio
    async def test_build_container_paper_mode(self):
        settings = Settings(trade_mode=TradeMode.PAPER, polymarket_private_key="")
        container = await build_container(settings=settings, db_path=":memory:")
        try:
            assert container.pricing is None  # No key = no pricing
            assert container.settings.trade_mode == TradeMode.PAPER
            assert container.scan_opportunities is not None
            assert container.execute_trade is not None
            assert container.reconcile_positions is not None
            assert container.reconcile_on_startup is not None
            assert container.monitor_positions is not None
            assert container.unwind_position is not None
        finally:
            await close_container(container)

    @pytest.mark.asyncio
    async def test_container_migrations_run(self):
        settings = Settings(trade_mode=TradeMode.PAPER, polymarket_private_key="")
        container = await build_container(settings=settings, db_path=":memory:")
        try:
            # Verify tables exist
            async with container.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ) as cur:
                tables = {row[0] for row in await cur.fetchall()}
            assert "positions" in tables
            assert "opportunities" in tables
        finally:
            await close_container(container)

    @pytest.mark.asyncio
    async def test_close_container_is_safe(self):
        settings = Settings(trade_mode=TradeMode.PAPER, polymarket_private_key="")
        container = await build_container(settings=settings, db_path=":memory:")
        await close_container(container)
        # Should not raise even after close
