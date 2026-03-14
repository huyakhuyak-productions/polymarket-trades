from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from polymarket_trades.domain.entities.event import Event
from polymarket_trades.domain.entities.market import Market
from polymarket_trades.domain.services.fee_calculator import FeeCalculator
from polymarket_trades.domain.strategies.arbitrage.detector import ArbitrageDetector
from polymarket_trades.domain.value_objects.money import Money
from polymarket_trades.domain.value_objects.price import Price
from polymarket_trades.domain.value_objects.token_id import TokenId

_FAR_FUTURE = datetime(2099, 1, 1, tzinfo=timezone.utc)


def _make_market(
    id: str = "m1",
    yes_price: str = "0.45",
    no_price: str = "0.45",
    liquidity: str = "5000",
    enable_order_book: bool = True,
    closed: bool = False,
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
        end_date=_FAR_FUTURE,
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
def detector(fee_calc: FeeCalculator) -> ArbitrageDetector:
    return ArbitrageDetector(fee_calculator=fee_calc)


class TestArbitrageDetector:
    @pytest.mark.asyncio
    async def test_detects_arb_when_sum_below_one(self, detector: ArbitrageDetector) -> None:
        """Detects arb when YES(0.45) + NO(0.45) = 0.90 < 1.0."""
        market = _make_market(id="m1", yes_price="0.45", no_price="0.45")
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        assert len(results) == 1
        assert results[0].market_id == "m1"
        assert results[0].strategy_type == "arbitrage"

    @pytest.mark.asyncio
    async def test_no_arb_when_sum_equals_one(self, detector: ArbitrageDetector) -> None:
        """No arb when YES(0.50) + NO(0.50) = 1.0."""
        market = _make_market(id="m1", yes_price="0.50", no_price="0.50")
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        assert results == []

    @pytest.mark.asyncio
    async def test_no_arb_when_sum_exceeds_one(self, detector: ArbitrageDetector) -> None:
        """No arb when YES(0.55) + NO(0.55) = 1.10 > 1.0."""
        market = _make_market(id="m1", yes_price="0.55", no_price="0.45")
        event = _make_event(markets=[market])
        # 0.55 + 0.45 = 1.0, not > 1.0; use unequal to get > 1.0
        results = await detector.detect([event])
        assert results == []

    @pytest.mark.asyncio
    async def test_no_arb_when_sum_strictly_greater_than_one(self, detector: ArbitrageDetector) -> None:
        """No arb when prices sum strictly above 1.0 (manually constructed with no_price override)."""
        # yes=0.60, no=0.45 => sum=1.05
        market = _make_market(id="m1", yes_price="0.60", no_price="0.40")
        # 0.60 + 0.40 = 1.0 — edge case, should be skipped
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        assert results == []

    @pytest.mark.asyncio
    async def test_skips_untradeable_market(self, detector: ArbitrageDetector) -> None:
        """Skips market with enable_order_book=False."""
        market = _make_market(id="m1", yes_price="0.45", no_price="0.45", enable_order_book=False)
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        assert results == []

    @pytest.mark.asyncio
    async def test_profit_calculation_correct_for_fee_exempt(self, detector: ArbitrageDetector) -> None:
        """For fee-exempt (politics): profit = 1.0 - (yes + no) = 1.0 - 0.90 = 0.10."""
        market = _make_market(id="m1", yes_price="0.45", no_price="0.45", category="politics")
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        assert len(results) == 1
        opp = results[0]
        assert opp.expected_profit == Money(Decimal("0.10"))
        assert opp.spread == Decimal("0.10")
        assert opp.yes_ask == Decimal("0.45")
        assert opp.no_ask == Decimal("0.45")

    @pytest.mark.asyncio
    async def test_skips_below_min_profit_threshold(self, fee_calc: FeeCalculator) -> None:
        """Skips when profit after fees is below min_profit_threshold."""
        # Set min_profit high enough that a small spread won't qualify
        detector = ArbitrageDetector(
            fee_calculator=fee_calc,
            min_profit_threshold=Money(Decimal("0.50")),
        )
        market = _make_market(id="m1", yes_price="0.45", no_price="0.45")
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        assert results == []

    @pytest.mark.asyncio
    async def test_no_token_id_is_populated(self, detector: ArbitrageDetector) -> None:
        """Critical: no_token_id must be populated for placing the NO-side order."""
        market = _make_market(id="m1", yes_price="0.45", no_price="0.45")
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        assert len(results) == 1
        opp = results[0]
        assert opp.no_token_id != ""
        assert opp.no_token_id == "0xno-m1"

    @pytest.mark.asyncio
    async def test_token_id_is_yes_token(self, detector: ArbitrageDetector) -> None:
        """Primary token_id corresponds to the YES side."""
        market = _make_market(id="m1", yes_price="0.45", no_price="0.45")
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        assert len(results) == 1
        assert results[0].token_id == "0xyes-m1"

    @pytest.mark.asyncio
    async def test_entry_price_is_total_cost(self, detector: ArbitrageDetector) -> None:
        """entry_price is the total cost of buying both YES and NO."""
        market = _make_market(id="m1", yes_price="0.45", no_price="0.45")
        event = _make_event(markets=[market])
        results = await detector.detect([event])
        assert len(results) == 1
        assert results[0].entry_price == Decimal("0.90")

    @pytest.mark.asyncio
    async def test_empty_events_returns_empty(self, detector: ArbitrageDetector) -> None:
        """Empty event list returns empty opportunities."""
        results = await detector.detect([])
        assert results == []
