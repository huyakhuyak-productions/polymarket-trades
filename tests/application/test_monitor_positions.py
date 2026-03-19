from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from polymarket_trades.application.use_cases.monitor_positions import MonitorPositions
from polymarket_trades.domain.entities.position import Position
from polymarket_trades.domain.value_objects.outcome import Side
from polymarket_trades.domain.value_objects.resolution_outcome import ResolutionOutcome
from polymarket_trades.domain.value_objects.token_id import TokenId
from polymarket_trades.domain.value_objects.trade_mode import PositionStatus, TradeMode


def _make_resolved_position(
    strategy: str = "near_certain",
    pnl: Decimal = Decimal("1.50"),
) -> Position:
    now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)
    return Position(
        id=uuid.uuid4(),
        opportunity_type=strategy,
        market_id="m1",
        token_id=TokenId("0xyes"),
        side=Side.YES,
        event_title="Test",
        entry_price=Decimal("0.96"),
        quantity=Decimal("50"),
        detected_at=now,
        entry_time=now,
        current_price=Decimal("1.0"),
        resolution_outcome=ResolutionOutcome.YES,
        exit_price=Decimal("1.0"),
        pnl=pnl,
        fees_estimated=Decimal("0.10"),
        mode=TradeMode.PAPER,
        status=PositionStatus.PNL_CALCULATED,
    )


class TestMonitorPositions:
    @pytest.mark.asyncio
    async def test_generates_report_by_strategy(self):
        pos_tracker = AsyncMock()
        pos_tracker.get_all_positions.return_value = [
            _make_resolved_position(strategy="near_certain", pnl=Decimal("1.50")),
            _make_resolved_position(strategy="near_certain", pnl=Decimal("-0.50")),
            _make_resolved_position(strategy="arbitrage", pnl=Decimal("0.80")),
        ]

        uc = MonitorPositions(position_tracker=pos_tracker)
        reports = await uc.execute()

        assert len(reports) == 2
        # Reports are sorted by strategy name
        arb = reports[0]
        assert arb.strategy == "arbitrage"
        assert arb.trades == 1
        assert arb.wins == 1
        assert arb.total_pnl == Decimal("0.80")
        assert arb.total_cost == Decimal("48.00")
        # 0.80 / 48 * 100 ≈ 1.667%
        assert abs(arb.total_return_pct - Decimal("1.667")) < Decimal("0.01")

        nc = reports[1]
        assert nc.strategy == "near_certain"
        assert nc.trades == 2
        assert nc.wins == 1
        assert nc.total_pnl == Decimal("1.00")
        assert nc.total_cost == Decimal("96.00")
        # 1.00 / 96 * 100 ≈ 1.042%
        assert abs(nc.total_return_pct - Decimal("1.042")) < Decimal("0.01")

    @pytest.mark.asyncio
    async def test_empty_positions(self):
        pos_tracker = AsyncMock()
        pos_tracker.get_all_positions.return_value = []

        uc = MonitorPositions(position_tracker=pos_tracker)
        reports = await uc.execute()

        assert reports == []

    @pytest.mark.asyncio
    async def test_skips_positions_without_pnl(self):
        now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)
        open_pos = Position(
            id=uuid.uuid4(),
            opportunity_type="near_certain",
            market_id="m1",
            token_id=TokenId("0xyes"),
            side=Side.YES,
            event_title="Test",
            entry_price=Decimal("0.96"),
            quantity=Decimal("50"),
            detected_at=now,
            entry_time=now,
            current_price=Decimal("0.96"),
            resolution_outcome=None,
            exit_price=None,
            pnl=None,
            fees_estimated=Decimal("0.10"),
            mode=TradeMode.PAPER,
            status=PositionStatus.MONITORING,
        )
        pos_tracker = AsyncMock()
        pos_tracker.get_all_positions.return_value = [open_pos]

        uc = MonitorPositions(position_tracker=pos_tracker)
        reports = await uc.execute()

        assert reports == []

    @pytest.mark.asyncio
    async def test_win_pct_calculation(self):
        pos_tracker = AsyncMock()
        pos_tracker.get_all_positions.return_value = [
            _make_resolved_position(pnl=Decimal("1.50")),
            _make_resolved_position(pnl=Decimal("2.00")),
            _make_resolved_position(pnl=Decimal("-1.00")),
        ]

        uc = MonitorPositions(position_tracker=pos_tracker)
        reports = await uc.execute()

        assert len(reports) == 1
        report = reports[0]
        assert report.trades == 3
        assert report.wins == 2
        # 2/3 * 100 ≈ 66.67
        assert report.win_pct > Decimal("66") and report.win_pct < Decimal("67")
