from datetime import datetime, timezone
from decimal import Decimal
import pytest
from polymarket_trades.domain.entities.market import Market
from polymarket_trades.domain.entities.event import Event
from polymarket_trades.domain.value_objects.price import Price
from polymarket_trades.domain.value_objects.token_id import TokenId
from polymarket_trades.domain.value_objects.outcome import Outcome, Side


def make_market(**overrides) -> Market:
    defaults = {
        "id": "market-1", "question": "Will X happen?", "condition_id": "cond-1",
        "slug": "will-x-happen", "yes_token_id": TokenId("0xyes"), "no_token_id": TokenId("0xno"),
        "yes_price": Price(Decimal("0.75")), "no_price": Price(Decimal("0.25")),
        "liquidity": Decimal("5000"), "volume": Decimal("10000"),
        "enable_order_book": True, "tick_size": Decimal("0.01"), "neg_risk": False,
        "end_date": datetime(2026, 6, 1, tzinfo=timezone.utc), "closed": False, "category": "",
    }
    defaults.update(overrides)
    return Market(**defaults)


class TestMarket:
    def test_create_market(self):
        m = make_market()
        assert m.id == "market-1"
        assert m.yes_price == Price(Decimal("0.75"))

    def test_is_tradeable_when_order_book_enabled(self):
        m = make_market(enable_order_book=True, closed=False)
        assert m.is_tradeable is True

    def test_not_tradeable_when_order_book_disabled(self):
        m = make_market(enable_order_book=False)
        assert m.is_tradeable is False

    def test_not_tradeable_when_closed(self):
        m = make_market(closed=True)
        assert m.is_tradeable is False

    def test_minutes_to_close(self):
        m = make_market(end_date=datetime(2099, 1, 1, tzinfo=timezone.utc))
        assert m.minutes_to_close > 0

    def test_minutes_to_close_past_end_date(self):
        m = make_market(end_date=datetime(2020, 1, 1, tzinfo=timezone.utc))
        assert m.minutes_to_close <= 0

    def test_minutes_to_close_none_end_date(self):
        m = make_market(end_date=None)
        assert m.minutes_to_close == float("inf")

    def test_tick_size_validation(self):
        for tick in [Decimal("0.1"), Decimal("0.01"), Decimal("0.001"), Decimal("0.0001")]:
            m = make_market(tick_size=tick)
            assert m.tick_size == tick

    def test_outcomes_property(self):
        m = make_market(yes_price=Price(Decimal("0.60")), no_price=Price(Decimal("0.40")))
        outcomes = m.outcomes
        assert len(outcomes) == 2
        assert outcomes[0].side == Side.YES
        assert outcomes[1].side == Side.NO


def make_event(**overrides) -> Event:
    defaults = {
        "id": "event-1", "title": "Test Event", "slug": "test-event", "description": "A test event",
        "start_date": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "end_date": datetime(2026, 6, 1, tzinfo=timezone.utc),
        "active": True, "closed": False, "archived": False,
        "liquidity": Decimal("10000"), "volume": Decimal("50000"),
        "neg_risk": False, "markets": [make_market()], "category": "politics",
    }
    defaults.update(overrides)
    return Event(**defaults)


class TestEvent:
    def test_create_event(self):
        e = make_event()
        assert e.id == "event-1"
        assert len(e.markets) == 1

    def test_tradeable_markets_filters_untradeable(self):
        m1 = make_market(id="m1", enable_order_book=True, closed=False)
        m2 = make_market(id="m2", enable_order_book=False, closed=False)
        m3 = make_market(id="m3", enable_order_book=True, closed=True)
        e = make_event(markets=[m1, m2, m3])
        assert len(e.tradeable_markets) == 1
        assert e.tradeable_markets[0].id == "m1"

    def test_is_multi_outcome(self):
        markets = [make_market(id=f"m{i}") for i in range(4)]
        e = make_event(markets=markets, neg_risk=True)
        assert e.is_multi_outcome is True

    def test_not_multi_outcome_with_few_markets(self):
        e = make_event(markets=[make_market()], neg_risk=True)
        assert e.is_multi_outcome is False

    def test_not_multi_outcome_without_neg_risk(self):
        markets = [make_market(id=f"m{i}") for i in range(4)]
        e = make_event(markets=markets, neg_risk=False)
        assert e.is_multi_outcome is False
