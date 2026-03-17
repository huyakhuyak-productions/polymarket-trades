from __future__ import annotations
from decimal import Decimal
from polymarket_trades.domain.entities.event import Event
from polymarket_trades.domain.services.fee_calculator import FeeCalculator, MarketCategory
from polymarket_trades.domain.strategies.arbitrage.opportunity import ArbitrageOpportunity
from polymarket_trades.domain.value_objects.money import Money


class ArbitrageDetector:
    """Buy-side only (v1): buy YES + NO when sum < 1.0."""

    def __init__(
        self,
        fee_calculator: FeeCalculator,
        min_profit_threshold: Money = Money(Decimal("0.001")),
    ) -> None:
        self._fee_calc = fee_calculator
        self._min_profit = min_profit_threshold

    async def detect(self, events: list[Event]) -> list[ArbitrageOpportunity]:
        opportunities: list[ArbitrageOpportunity] = []
        for event in events:
            for market in event.tradeable_markets:
                yes_ask = market.yes_price.value
                no_ask = market.no_price.value
                total_cost = yes_ask + no_ask
                if total_cost >= Decimal("1.0"):
                    continue
                spread = Decimal("1.0") - total_cost
                category = MarketCategory.from_string(market.category)
                yes_fee = self._fee_calc.estimate(
                    price=market.yes_price,
                    quantity=Decimal("1"),
                    category=category,
                    is_maker=False,
                )
                no_fee = self._fee_calc.estimate(
                    price=market.no_price,
                    quantity=Decimal("1"),
                    category=category,
                    is_maker=False,
                )
                profit_per_share = spread - yes_fee.value - no_fee.value
                if profit_per_share <= self._min_profit.value:
                    continue
                opportunities.append(
                    ArbitrageOpportunity(
                        strategy_type="arbitrage",
                        market_id=market.id,
                        token_id=market.yes_token_id.value,
                        event_title=event.title,
                        expected_profit=Money(profit_per_share),
                        entry_price=total_cost,
                        event_slug=event.slug,
                        no_token_id=market.no_token_id.value,
                        yes_ask=yes_ask,
                        no_ask=no_ask,
                        spread=spread,
                    )
                )
        return opportunities
