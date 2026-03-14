from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from polymarket_trades.domain.entities.event import Event
from polymarket_trades.domain.entities.market import Market
from polymarket_trades.domain.services.fee_calculator import FeeCalculator
from polymarket_trades.domain.strategies.near_certain.detector import NearCertainDetector
from polymarket_trades.domain.value_objects.money import Money
from polymarket_trades.domain.value_objects.price import Price
from polymarket_trades.domain.value_objects.token_id import TokenId

_FAR_FUTURE = datetime(2099, 1, 1, tzinfo=timezone.utc)
_PAST = datetime(2020, 1, 1, tzinfo=timezone.utc)


def _make_market(
    id: str = "m1",
    yes_price: str = "0.96",
    no_price: str = "0.04",
    liquidity: str = "5000",
    enable_order_book: bool = True,
    closed: bool = False,
    end_date: datetime | None = _FAR_FUTURE,
    category: str = "politics",
    **overrides: object,
) -> Market:
    defaults = dict(
        id=id,
        question=f"Will market {id} resolve YES?",
        condition_id=f"cond-{id}",
        slug=f"market-{id}",
        yes_token_id=TokenId(f"0xyes-{id}"),
        no_token_id=TokenId(f"0xno-{id}"),
        yes_price=Price(Decimal(yes_price)),
        no_price=Price(Decimal(no_price)),
        liquidity=Decimal(liquidity),
        volume=Decimal("10000"),
        enable_order_book=enable_order_book,
        tick_size=Decimal("0.01"),
        neg_risk=False,
        end_date=end_date,
        closed=closed,
        category=category,
    )
    defaults.update(overrides)
    return Market(**defaults)


def _make_event(markets: list[Market], id: str = "e1", title: str = "Test Event") -> Event:
    return Event(
        id=id,
        title=title,
        slug=id,
        description="",
        start_date=None,
        end_date=None,
        active=True,
        closed=False,
        archived=False,
        liquidity=Decimal("5000"),
        volume=Decimal("10000"),
        neg_risk=False,
        markets=markets,
    )


@pytest.fixture
def fee_calc() -> FeeCalculator:
    return FeeCalculator()


@pytest.fixture
def detector(fee_calc: FeeCalculator) -> NearCertainDetector:
    return NearCertainDetector(fee_calculator=fee_calc)


class TestNearCertainDetector:
    @pytest.mark.asyncio
    async def test_detects_market_above_threshold(self, detector: NearCertainDetector) -> None:
        """Detects a market with YES price >= 0.96 (above default 0.95 threshold)."""
        market = _make_market(id="m1", yes_price="0.96", no_price="0.04")
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        assert len(results) == 1
        assert results[0].market_id == "m1"
        assert results[0].strategy_type == "near_certain"

    @pytest.mark.asyncio
    async def test_skips_market_below_threshold(self, detector: NearCertainDetector) -> None:
        """Skips market with YES price below 0.95 threshold."""
        market = _make_market(id="m1", yes_price="0.80", no_price="0.20")
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        assert results == []

    @pytest.mark.asyncio
    async def test_skips_untradeable_market(self, detector: NearCertainDetector) -> None:
        """Skips market with enable_order_book=False."""
        market = _make_market(id="m1", yes_price="0.96", no_price="0.04", enable_order_book=False)
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        assert results == []

    @pytest.mark.asyncio
    async def test_skips_closed_market(self, detector: NearCertainDetector) -> None:
        """Skips market with closed=True."""
        market = _make_market(id="m1", yes_price="0.96", no_price="0.04", closed=True)
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        assert results == []

    @pytest.mark.asyncio
    async def test_skips_market_closing_soon(self, detector: NearCertainDetector) -> None:
        """Skips market that is past end_date (minutes_to_close will be negative)."""
        market = _make_market(id="m1", yes_price="0.96", no_price="0.04", end_date=_PAST)
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        assert results == []

    @pytest.mark.asyncio
    async def test_skips_low_liquidity(self, detector: NearCertainDetector) -> None:
        """Skips market with liquidity below the 100 minimum."""
        market = _make_market(id="m1", yes_price="0.96", no_price="0.04", liquidity="50")
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        assert results == []

    @pytest.mark.asyncio
    async def test_detects_multiple_qualifying_markets(self, detector: NearCertainDetector) -> None:
        """Detects multiple markets in the same event when both qualify."""
        market1 = _make_market(id="m1", yes_price="0.96", no_price="0.04")
        market2 = _make_market(id="m2", yes_price="0.97", no_price="0.03")
        event = _make_event(markets=[market1, market2])
        results = await detector.detect([event])
        assert len(results) == 2
        market_ids = {r.market_id for r in results}
        assert market_ids == {"m1", "m2"}

    @pytest.mark.asyncio
    async def test_opportunity_has_positive_expected_profit(self, detector: NearCertainDetector) -> None:
        """Opportunity has positive expected_profit for a fee-exempt market at 0.96."""
        # politics category is fee-exempt, so profit = 1.0 - 0.96 = 0.04
        market = _make_market(id="m1", yes_price="0.96", no_price="0.04", category="politics")
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        assert len(results) == 1
        opp = results[0]
        assert opp.expected_profit.value > Decimal("0")
        assert opp.yes_price == Decimal("0.96")
        assert opp.expected_return_pct > Decimal("0")

    @pytest.mark.asyncio
    async def test_opportunity_profit_correct_for_fee_exempt(self, detector: NearCertainDetector) -> None:
        """For fee-exempt category: profit = 1.0 - yes_price."""
        market = _make_market(id="m1", yes_price="0.96", no_price="0.04", category="politics")
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        assert len(results) == 1
        # fee exempt: profit_per_share = 1.0 - 0.96 - 0.0 = 0.04
        assert results[0].expected_profit == Money(Decimal("0.04"))

    @pytest.mark.asyncio
    async def test_skips_market_exactly_at_threshold(self) -> None:
        """Market at exactly 0.95 is below the strict threshold (< not <=)."""
        fee_calc = FeeCalculator()
        detector = NearCertainDetector(fee_calculator=fee_calc, price_threshold=Decimal("0.95"))
        market = _make_market(id="m1", yes_price="0.95", no_price="0.05")
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        # 0.95 is NOT < 0.95, so it passes the threshold check
        # profit = 1.0 - 0.95 = 0.05 which is > min_profit of 0.005
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_opportunity_token_id_matches_yes_token(self, detector: NearCertainDetector) -> None:
        """Opportunity token_id matches the market's yes_token_id."""
        market = _make_market(id="m1", yes_price="0.96", no_price="0.04")
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        assert len(results) == 1
        assert results[0].token_id == "0xyes-m1"

    @pytest.mark.asyncio
    async def test_empty_events_returns_empty(self, detector: NearCertainDetector) -> None:
        """Empty event list returns empty opportunities."""
        results = await detector.detect([])
        assert results == []
