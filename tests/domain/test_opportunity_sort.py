from __future__ import annotations

from decimal import Decimal

from polymarket_trades.domain.strategies.opportunity import Opportunity
from polymarket_trades.domain.value_objects.money import Money


def _opp(
    minutes_to_close: float = 60.0,
    profit: Decimal = Decimal("2.00"),
    entry_price: Decimal = Decimal("0.96"),
    market_id: str = "m1",
) -> Opportunity:
    return Opportunity(
        strategy_type="near_certain",
        market_id=market_id,
        token_id="0xyes",
        event_title="Test",
        expected_profit=Money(profit),
        entry_price=entry_price,
        minutes_to_close=minutes_to_close,
    )


class TestOpportunitySortKey:
    def test_sort_key_prefers_shorter_time_to_close(self):
        soon = _opp(minutes_to_close=30.0)
        later = _opp(minutes_to_close=120.0)

        assert soon.sort_key < later.sort_key

    def test_sort_key_breaks_ties_by_return_pct(self):
        """Among same time-to-close, higher return % should sort first."""
        high_return = _opp(
            minutes_to_close=60.0,
            profit=Decimal("4.00"),
            entry_price=Decimal("0.96"),
        )
        low_return = _opp(
            minutes_to_close=60.0,
            profit=Decimal("1.00"),
            entry_price=Decimal("0.96"),
        )

        assert high_return.sort_key < low_return.sort_key

    def test_sort_key_handles_zero_entry_price(self):
        """Zero entry price should not crash; treat as highest return."""
        zero_price = _opp(entry_price=Decimal("0"), profit=Decimal("1.00"))
        normal = _opp(entry_price=Decimal("0.96"), profit=Decimal("1.00"))

        # Zero entry_price → infinite return → should sort before normal
        assert zero_price.sort_key < normal.sort_key

    def test_sorted_list_of_opportunities(self):
        opps = [
            _opp(minutes_to_close=120.0, profit=Decimal("2.00"), entry_price=Decimal("0.96"), market_id="far_low"),
            _opp(minutes_to_close=30.0, profit=Decimal("1.00"), entry_price=Decimal("0.96"), market_id="soon_low"),
            _opp(minutes_to_close=30.0, profit=Decimal("4.00"), entry_price=Decimal("0.96"), market_id="soon_high"),
            _opp(minutes_to_close=60.0, profit=Decimal("2.00"), entry_price=Decimal("0.96"), market_id="mid"),
            _opp(minutes_to_close=120.0, profit=Decimal("5.00"), entry_price=Decimal("0.96"), market_id="far_high"),
        ]

        sorted_opps = sorted(opps, key=lambda o: o.sort_key)
        ids = [o.market_id for o in sorted_opps]

        assert ids == ["soon_high", "soon_low", "mid", "far_high", "far_low"]
