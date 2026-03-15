from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from polymarket_trades.application.use_cases.scan_opportunities import ScanOpportunities
from polymarket_trades.domain.entities.event import Event
from polymarket_trades.domain.entities.position import Position
from polymarket_trades.domain.services.scanner import Scanner
from polymarket_trades.domain.strategies.opportunity import Opportunity
from polymarket_trades.domain.value_objects.money import Money
from polymarket_trades.domain.value_objects.outcome import Side
from polymarket_trades.domain.value_objects.token_id import TokenId
from polymarket_trades.domain.value_objects.trade_mode import PositionStatus, TradeMode


def _make_event(event_id: str = "e1") -> Event:
    return Event(
        id=event_id,
        title="Test Event",
        slug="test",
        description="",
        start_date=None,
        end_date=None,
        active=True,
        closed=False,
        archived=False,
        liquidity=Decimal("1000"),
        volume=Decimal("5000"),
        neg_risk=False,
        markets=[],
    )


def _make_opportunity(market_id: str = "m1", token_id: str = "0xyes") -> Opportunity:
    return Opportunity(
        strategy_type="near_certain",
        market_id=market_id,
        token_id=token_id,
        event_title="Test",
        expected_profit=Money(Decimal("2.00")),
        entry_price=Decimal("0.96"),
    )


def _make_position(market_id: str = "m1", status: PositionStatus = PositionStatus.MONITORING) -> Position:
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


class TestScanOpportunities:
    @pytest.mark.asyncio
    async def test_paginates_events(self):
        event_discovery = AsyncMock()
        page1 = [_make_event("e1"), _make_event("e2")]
        page2 = [_make_event("e3")]
        page3 = []
        event_discovery.fetch_active_events.side_effect = [page1, page2, page3]

        scanner = AsyncMock(spec=Scanner)
        scanner.scan.return_value = []

        opp_store = AsyncMock()
        pos_tracker = AsyncMock()

        uc = ScanOpportunities(
            event_discovery=event_discovery,
            scanner=scanner,
            opportunity_store=opp_store,
            position_tracker=pos_tracker,
            page_size=2,
        )

        result = await uc.execute()

        assert event_discovery.fetch_active_events.call_count == 3
        scanner.scan.assert_called_once()
        events_passed = scanner.scan.call_args[0][0]
        assert len(events_passed) == 3
        assert result == []

    @pytest.mark.asyncio
    async def test_deduplicates_existing_opportunities(self):
        event_discovery = AsyncMock()
        event_discovery.fetch_active_events.side_effect = [
            [_make_event()],
            [],
        ]

        scanner = AsyncMock(spec=Scanner)
        opp = _make_opportunity()
        scanner.scan.return_value = [opp]

        opp_store = AsyncMock()
        opp_store.find_existing.return_value = opp  # Already exists

        pos_tracker = AsyncMock()

        uc = ScanOpportunities(
            event_discovery=event_discovery,
            scanner=scanner,
            opportunity_store=opp_store,
            position_tracker=pos_tracker,
        )

        result = await uc.execute()

        assert result == []
        opp_store.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_markets_with_open_positions(self):
        event_discovery = AsyncMock()
        event_discovery.fetch_active_events.side_effect = [
            [_make_event()],
            [],
        ]

        scanner = AsyncMock(spec=Scanner)
        opp = _make_opportunity(market_id="m1")
        scanner.scan.return_value = [opp]

        opp_store = AsyncMock()
        opp_store.find_existing.return_value = None

        pos_tracker = AsyncMock()
        pos_tracker.get_position_by_market.return_value = _make_position(
            market_id="m1", status=PositionStatus.MONITORING
        )

        uc = ScanOpportunities(
            event_discovery=event_discovery,
            scanner=scanner,
            opportunity_store=opp_store,
            position_tracker=pos_tracker,
        )

        result = await uc.execute()

        assert result == []
        opp_store.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_saves_and_returns_viable_opportunities(self):
        event_discovery = AsyncMock()
        event_discovery.fetch_active_events.side_effect = [
            [_make_event()],
            [],
        ]

        scanner = AsyncMock(spec=Scanner)
        opp = _make_opportunity()
        scanner.scan.return_value = [opp]

        opp_store = AsyncMock()
        opp_store.find_existing.return_value = None

        pos_tracker = AsyncMock()
        pos_tracker.get_position_by_market.return_value = None

        uc = ScanOpportunities(
            event_discovery=event_discovery,
            scanner=scanner,
            opportunity_store=opp_store,
            position_tracker=pos_tracker,
        )

        result = await uc.execute()

        assert len(result) == 1
        assert result[0] is opp
        opp_store.save.assert_called_once_with(opp)

    @pytest.mark.asyncio
    async def test_allows_closed_position_market(self):
        """A market with a closed/resolved position should not block new opportunities."""
        event_discovery = AsyncMock()
        event_discovery.fetch_active_events.side_effect = [
            [_make_event()],
            [],
        ]

        scanner = AsyncMock(spec=Scanner)
        opp = _make_opportunity(market_id="m1")
        scanner.scan.return_value = [opp]

        opp_store = AsyncMock()
        opp_store.find_existing.return_value = None

        pos_tracker = AsyncMock()
        pos_tracker.get_position_by_market.return_value = _make_position(
            market_id="m1", status=PositionStatus.PNL_CALCULATED
        )

        uc = ScanOpportunities(
            event_discovery=event_discovery,
            scanner=scanner,
            opportunity_store=opp_store,
            position_tracker=pos_tracker,
        )

        result = await uc.execute()

        assert len(result) == 1
        opp_store.save.assert_called_once()
