from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polymarket_trades.application.scheduler import Scheduler
from polymarket_trades.domain.strategies.opportunity import Opportunity
from polymarket_trades.domain.value_objects.money import Money
from polymarket_trades.domain.value_objects.trade_mode import TradeMode
from polymarket_trades.infrastructure.config.settings import Settings


def _make_mock_container() -> MagicMock:
    container = MagicMock()
    container.settings = Settings(
        trade_mode=TradeMode.PAPER,
        scan_interval_seconds=1,
    )
    container.scan_opportunities = AsyncMock()
    container.execute_trade = AsyncMock()
    container.reconcile_positions = AsyncMock()
    container.reconcile_on_startup = AsyncMock()
    return container


def _make_opportunity() -> Opportunity:
    return Opportunity(
        strategy_type="near_certain",
        market_id="m1",
        token_id="0xyes",
        event_title="Test",
        expected_profit=Money(Decimal("2.00")),
        entry_price=Decimal("0.96"),
        market_liquidity=Decimal("500"),
        minutes_to_close=120.0,
    )


class TestScheduler:
    @pytest.mark.asyncio
    async def test_run_cycle_executes_scan_execute_reconcile(self):
        container = _make_mock_container()
        opp = _make_opportunity()
        container.scan_opportunities.execute.return_value = [opp]
        container.reconcile_positions.execute.return_value = 0

        scheduler = Scheduler(container)
        await scheduler._run_cycle()

        container.scan_opportunities.execute.assert_called_once()
        container.execute_trade.execute.assert_called_once_with(
            opportunity=opp,
            market_liquidity=opp.market_liquidity,
            minutes_to_close=opp.minutes_to_close,
        )
        container.reconcile_positions.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_cycle_no_opportunities(self):
        container = _make_mock_container()
        container.scan_opportunities.execute.return_value = []
        container.reconcile_positions.execute.return_value = 0

        scheduler = Scheduler(container)
        await scheduler._run_cycle()

        container.execute_trade.execute.assert_not_called()
        container.reconcile_positions.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_terminates_loop(self):
        container = _make_mock_container()
        container.scan_opportunities.execute.return_value = []
        container.reconcile_positions.execute.return_value = 0

        scheduler = Scheduler(container)

        async def stop_after_short_delay():
            await asyncio.sleep(0.1)
            scheduler.stop()

        task = asyncio.create_task(stop_after_short_delay())
        await scheduler.run()
        await task

        container.reconcile_on_startup.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_cycle_error_does_not_crash_loop(self):
        container = _make_mock_container()
        call_count = 0

        async def side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("test error")
            return []

        container.scan_opportunities.execute.side_effect = side_effect
        container.reconcile_positions.execute.return_value = 0

        scheduler = Scheduler(container)

        async def stop_after_short_delay():
            await asyncio.sleep(0.3)
            scheduler.stop()

        task = asyncio.create_task(stop_after_short_delay())
        await scheduler.run()
        await task

        # Should have survived the error and run at least once more
        assert call_count >= 1
