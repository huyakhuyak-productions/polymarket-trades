from datetime import datetime, timezone
from decimal import Decimal
import pytest
from polymarket_trades.domain.entities.event import Event
from polymarket_trades.domain.entities.market import Market
from polymarket_trades.domain.services.scanner import Scanner
from polymarket_trades.domain.strategies.opportunity import Opportunity
from polymarket_trades.domain.value_objects.money import Money
from polymarket_trades.domain.value_objects.price import Price
from polymarket_trades.domain.value_objects.token_id import TokenId

def _make_event() -> Event:
    market = Market(id="m1", question="Q?", condition_id="c1", slug="q",
        yes_token_id=TokenId("0xyes"), no_token_id=TokenId("0xno"),
        yes_price=Price(Decimal("0.96")), no_price=Price(Decimal("0.04")),
        liquidity=Decimal("5000"), volume=Decimal("10000"), enable_order_book=True,
        tick_size=Decimal("0.01"), neg_risk=False,
        end_date=datetime(2026, 6, 1, tzinfo=timezone.utc), closed=False, category="")
    return Event(id="e1", title="E1", slug="e1", description="", start_date=None, end_date=None,
        active=True, closed=False, archived=False, liquidity=Decimal("5000"),
        volume=Decimal("10000"), neg_risk=False, markets=[market])

class FakeDetector:
    def __init__(self, opportunities: list[Opportunity]) -> None:
        self._opportunities = opportunities
    async def detect(self, events: list[Event]) -> list[Opportunity]:
        return self._opportunities

class TestScanner:
    @pytest.mark.asyncio
    async def test_runs_all_detectors(self):
        opp1 = Opportunity(strategy_type="a", market_id="m1", token_id="0x1",
            event_title="E", expected_profit=Money(Decimal("1")), entry_price=Decimal("0.95"))
        opp2 = Opportunity(strategy_type="b", market_id="m2", token_id="0x2",
            event_title="E", expected_profit=Money(Decimal("2")), entry_price=Decimal("0.50"))
        scanner = Scanner([FakeDetector([opp1]), FakeDetector([opp2])])
        results = await scanner.scan([_make_event()])
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_opportunities(self):
        scanner = Scanner([FakeDetector([])])
        assert await scanner.scan([_make_event()]) == []

    @pytest.mark.asyncio
    async def test_aggregates_from_multiple_detectors(self):
        opps = [Opportunity(strategy_type=f"s{i}", market_id=f"m{i}", token_id=f"0x{i}",
            event_title="E", expected_profit=Money(Decimal("1")), entry_price=Decimal("0.95")) for i in range(5)]
        scanner = Scanner([FakeDetector(opps[:2]), FakeDetector(opps[2:4]), FakeDetector([opps[4]])])
        assert len(await scanner.scan([_make_event()])) == 5

    @pytest.mark.asyncio
    async def test_runs_with_no_detectors(self):
        assert await Scanner([]).scan([_make_event()]) == []
