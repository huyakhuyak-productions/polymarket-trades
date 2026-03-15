from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from polymarket_trades.application.use_cases.reconcile_on_startup import ReconcileOnStartup
from polymarket_trades.application.use_cases.reconcile_positions import ReconcilePositions
from polymarket_trades.domain.entities.position import Position
from polymarket_trades.domain.value_objects.outcome import Side
from polymarket_trades.domain.value_objects.price import Price
from polymarket_trades.domain.value_objects.resolution_outcome import ResolutionOutcome
from polymarket_trades.domain.value_objects.token_id import TokenId
from polymarket_trades.domain.value_objects.trade_mode import PositionStatus, TradeMode


def _make_position(
    status: PositionStatus = PositionStatus.MONITORING,
    market_id: str = "m1",
) -> Position:
    now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)
    return Position(
        id=uuid.uuid4(),
        opportunity_type="near_certain",
        market_id=market_id,
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
        status=status,
    )


class TestReconcilePositions:
    @pytest.mark.asyncio
    async def test_resolves_closed_market(self):
        pos = _make_position()
        pos_tracker = AsyncMock()
        pos_tracker.get_open_positions.return_value = [pos]

        event_discovery = AsyncMock()
        event_discovery.is_market_resolved.return_value = (True, ResolutionOutcome.YES)

        uc = ReconcilePositions(
            position_tracker=pos_tracker,
            event_discovery=event_discovery,
            pricing=None,
        )

        count = await uc.execute()

        assert count == 1
        pos_tracker.update_position.assert_called_once()
        updated_pos = pos_tracker.update_position.call_args[0][0]
        assert updated_pos.status == PositionStatus.PNL_CALCULATED
        assert updated_pos.pnl is not None

    @pytest.mark.asyncio
    async def test_updates_price_when_pricing_available(self):
        pos = _make_position()
        pos_tracker = AsyncMock()
        pos_tracker.get_open_positions.return_value = [pos]

        event_discovery = AsyncMock()
        event_discovery.is_market_resolved.return_value = (False, None)

        pricing = AsyncMock()
        pricing.get_midpoint.return_value = Price(Decimal("0.98"))

        uc = ReconcilePositions(
            position_tracker=pos_tracker,
            event_discovery=event_discovery,
            pricing=pricing,
        )

        count = await uc.execute()

        assert count == 0
        updated_pos = pos_tracker.update_position.call_args[0][0]
        assert updated_pos.current_price == Decimal("0.98")

    @pytest.mark.asyncio
    async def test_handles_no_open_positions(self):
        pos_tracker = AsyncMock()
        pos_tracker.get_open_positions.return_value = []

        event_discovery = AsyncMock()

        uc = ReconcilePositions(
            position_tracker=pos_tracker,
            event_discovery=event_discovery,
            pricing=None,
        )

        count = await uc.execute()

        assert count == 0
        event_discovery.is_market_resolved.assert_not_called()


class TestReconcileOnStartup:
    @pytest.mark.asyncio
    async def test_recovers_entered_positions(self):
        pos = _make_position(status=PositionStatus.ENTERED)
        pos_tracker = AsyncMock()
        pos_tracker.get_open_positions.return_value = [pos]

        uc = ReconcileOnStartup(position_tracker=pos_tracker)
        await uc.execute()

        pos_tracker.update_position.assert_called_once()
        updated = pos_tracker.update_position.call_args[0][0]
        assert updated.status == PositionStatus.MONITORING

    @pytest.mark.asyncio
    async def test_no_action_when_no_orphans(self):
        pos = _make_position(status=PositionStatus.MONITORING)
        pos_tracker = AsyncMock()
        pos_tracker.get_open_positions.return_value = [pos]

        uc = ReconcileOnStartup(position_tracker=pos_tracker)
        await uc.execute()

        pos_tracker.update_position.assert_not_called()
