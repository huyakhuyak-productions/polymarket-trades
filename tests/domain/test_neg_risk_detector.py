from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from polymarket_trades.domain.entities.event import Event
from polymarket_trades.domain.entities.market import Market
from polymarket_trades.domain.services.fee_calculator import FeeCalculator
from polymarket_trades.domain.strategies.neg_risk_discount.detector import NegRiskDiscountDetector
from polymarket_trades.domain.value_objects.money import Money
from polymarket_trades.domain.value_objects.price import Price
from polymarket_trades.domain.value_objects.token_id import TokenId

_FAR_FUTURE = datetime(2099, 1, 1, tzinfo=timezone.utc)


def _make_market(
    id: str,
    yes_price: str,
    no_price: str | None = None,
    liquidity: str = "5000",
    enable_order_book: bool = True,
    closed: bool = False,
    category: str = "politics",
    **overrides: object,
) -> Market:
    # Compute a valid no_price if not provided: clamp to [0,1]
    yes_val = Decimal(yes_price)
    if no_price is None:
        no_val = max(Decimal("0"), min(Decimal("1"), Decimal("1") - yes_val))
    else:
        no_val = Decimal(no_price)
    defaults = dict(
        id=id,
        question=f"Will outcome {id} happen?",
        condition_id=f"cond-{id}",
        slug=f"market-{id}",
        yes_token_id=TokenId(f"0xyes-{id}"),
        no_token_id=TokenId(f"0xno-{id}"),
        yes_price=Price(yes_val),
        no_price=Price(no_val),
        liquidity=Decimal(liquidity),
        volume=Decimal("10000"),
        enable_order_book=enable_order_book,
        tick_size=Decimal("0.01"),
        neg_risk=True,
        end_date=_FAR_FUTURE,
        closed=closed,
        category=category,
    )
    defaults.update(overrides)
    return Market(**defaults)


def _make_multi_outcome_event(
    market_prices: list[str],
    neg_risk: bool = True,
    id: str = "e1",
    title: str = "Multi-outcome Event",
    enable_order_book: bool = True,
    liquidity: str = "5000",
) -> Event:
    markets = [
        _make_market(
            id=f"m{i}",
            yes_price=price,
            enable_order_book=enable_order_book,
            liquidity=liquidity,
        )
        for i, price in enumerate(market_prices)
    ]
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
        neg_risk=neg_risk,
        markets=markets,
    )


@pytest.fixture
def fee_calc() -> FeeCalculator:
    return FeeCalculator()


@pytest.fixture
def detector(fee_calc: FeeCalculator) -> NegRiskDiscountDetector:
    return NegRiskDiscountDetector(fee_calculator=fee_calc)


class TestNegRiskDiscountDetector:
    @pytest.mark.asyncio
    async def test_detects_discount_four_outcomes(self, detector: NegRiskDiscountDetector) -> None:
        """Detects discount: 4 outcomes at 0.20 each = 0.80 < 1.0."""
        event = _make_multi_outcome_event(market_prices=["0.20", "0.20", "0.20", "0.20"])
        results = await detector.detect([event])
        assert len(results) == 1
        assert results[0].strategy_type == "neg_risk_discount"
        assert results[0].event_title == "Multi-outcome Event"

    @pytest.mark.asyncio
    async def test_no_discount_when_sum_equals_one(self, detector: NegRiskDiscountDetector) -> None:
        """No discount when 4 outcomes at 0.25 = 1.0 exactly."""
        event = _make_multi_outcome_event(market_prices=["0.25", "0.25", "0.25", "0.25"])
        results = await detector.detect([event])
        assert results == []

    @pytest.mark.asyncio
    async def test_no_discount_when_sum_exceeds_one(self, detector: NegRiskDiscountDetector) -> None:
        """No discount when sum > 1.0."""
        event = _make_multi_outcome_event(market_prices=["0.30", "0.30", "0.30", "0.30"])
        results = await detector.detect([event])
        assert results == []

    @pytest.mark.asyncio
    async def test_skips_non_neg_risk_events(self, detector: NegRiskDiscountDetector) -> None:
        """Skips events without neg_risk=True."""
        event = _make_multi_outcome_event(
            market_prices=["0.20", "0.20", "0.20", "0.20"],
            neg_risk=False,
        )
        results = await detector.detect([event])
        assert results == []

    @pytest.mark.asyncio
    async def test_skips_fewer_than_three_markets(self, detector: NegRiskDiscountDetector) -> None:
        """Skips events with fewer than 3 markets (is_multi_outcome requires >= 3)."""
        # 2 markets: is_multi_outcome returns False for len < 3
        event = _make_multi_outcome_event(market_prices=["0.20", "0.20"])
        results = await detector.detect([event])
        assert results == []

    @pytest.mark.asyncio
    async def test_skips_if_any_outcome_has_order_book_disabled(self, detector: NegRiskDiscountDetector) -> None:
        """Skips when any market has enable_order_book=False (not all tradeable)."""
        markets = [
            _make_market(id="m0", yes_price="0.20", enable_order_book=True),
            _make_market(id="m1", yes_price="0.20", enable_order_book=True),
            _make_market(id="m2", yes_price="0.20", enable_order_book=False),  # disabled
            _make_market(id="m3", yes_price="0.20", enable_order_book=True),
        ]
        event = Event(
            id="e1", title="Multi-outcome Event", slug="e1", description="",
            start_date=None, end_date=None, active=True, closed=False, archived=False,
            liquidity=Decimal("5000"), volume=Decimal("10000"), neg_risk=True,
            markets=markets,
        )
        results = await detector.detect([event])
        assert results == []

    @pytest.mark.asyncio
    async def test_skips_if_any_outcome_has_low_liquidity(self, detector: NegRiskDiscountDetector) -> None:
        """Skips when any outcome has liquidity below min_liquidity_per_outcome."""
        markets = [
            _make_market(id="m0", yes_price="0.20", liquidity="5000"),
            _make_market(id="m1", yes_price="0.20", liquidity="5000"),
            _make_market(id="m2", yes_price="0.20", liquidity="50"),  # too low
            _make_market(id="m3", yes_price="0.20", liquidity="5000"),
        ]
        event = Event(
            id="e1", title="Multi-outcome Event", slug="e1", description="",
            start_date=None, end_date=None, active=True, closed=False, archived=False,
            liquidity=Decimal("5000"), volume=Decimal("10000"), neg_risk=True,
            markets=markets,
        )
        results = await detector.detect([event])
        assert results == []

    @pytest.mark.asyncio
    async def test_profit_equals_point_two_for_fee_exempt(self, detector: NegRiskDiscountDetector) -> None:
        """For fee-exempt (politics): profit = 1.0 - 0.80 = 0.20 with 4 outcomes at 0.20."""
        event = _make_multi_outcome_event(market_prices=["0.20", "0.20", "0.20", "0.20"])
        results = await detector.detect([event])
        assert len(results) == 1
        assert results[0].expected_profit == Money(Decimal("0.20"))

    @pytest.mark.asyncio
    async def test_leg_token_ids_has_correct_count(self, detector: NegRiskDiscountDetector) -> None:
        """leg_token_ids should contain one token_id per outcome market."""
        event = _make_multi_outcome_event(market_prices=["0.20", "0.20", "0.20", "0.20"])
        results = await detector.detect([event])
        assert len(results) == 1
        opp = results[0]
        assert len(opp.leg_token_ids) == 4
        assert len(opp.leg_prices) == 4

    @pytest.mark.asyncio
    async def test_leg_token_ids_content(self, detector: NegRiskDiscountDetector) -> None:
        """leg_token_ids values match the yes_token_ids of each market."""
        event = _make_multi_outcome_event(market_prices=["0.20", "0.20", "0.20", "0.20"])
        results = await detector.detect([event])
        assert len(results) == 1
        opp = results[0]
        expected_token_ids = [f"0xyes-m{i}" for i in range(4)]
        assert opp.leg_token_ids == expected_token_ids

    @pytest.mark.asyncio
    async def test_num_outcomes_correct(self, detector: NegRiskDiscountDetector) -> None:
        """num_outcomes matches the number of markets."""
        event = _make_multi_outcome_event(market_prices=["0.20", "0.20", "0.20", "0.20"])
        results = await detector.detect([event])
        assert len(results) == 1
        assert results[0].num_outcomes == 4

    @pytest.mark.asyncio
    async def test_total_cost_correct(self, detector: NegRiskDiscountDetector) -> None:
        """total_cost is the sum of all leg yes_prices."""
        event = _make_multi_outcome_event(market_prices=["0.20", "0.20", "0.20", "0.20"])
        results = await detector.detect([event])
        assert len(results) == 1
        assert results[0].total_cost == Decimal("0.80")

    @pytest.mark.asyncio
    async def test_skips_below_min_profit_threshold(self, fee_calc: FeeCalculator) -> None:
        """Skips when profit is below min_profit_threshold."""
        detector = NegRiskDiscountDetector(
            fee_calculator=fee_calc,
            min_profit_threshold=Money(Decimal("0.50")),
        )
        # 4 outcomes at 0.20 => profit = 0.20, below 0.50 threshold
        event = _make_multi_outcome_event(market_prices=["0.20", "0.20", "0.20", "0.20"])
        results = await detector.detect([event])
        assert results == []

    @pytest.mark.asyncio
    async def test_empty_events_returns_empty(self, detector: NegRiskDiscountDetector) -> None:
        """Empty event list returns empty opportunities."""
        results = await detector.detect([])
        assert results == []
