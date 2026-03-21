from __future__ import annotations
from decimal import Decimal
from polymarket_trades.domain.entities.event import Event
from polymarket_trades.domain.services.fee_calculator import FeeCalculator, MarketCategory
from polymarket_trades.domain.strategies.near_certain.opportunity import NearCertainOpportunity
from polymarket_trades.domain.value_objects.money import Money
from polymarket_trades.domain.value_objects.outcome import Side


class NearCertainDetector:
    def __init__(
        self,
        fee_calculator: FeeCalculator,
        price_threshold: Decimal = Decimal("0.95"),
        min_profit_threshold: Money = Money(Decimal("0.005")),
        min_liquidity: Decimal = Decimal("100"),
        min_minutes_to_close: int = 10,
    ) -> None:
        self._fee_calc = fee_calculator
        self._threshold = price_threshold
        self._min_profit = min_profit_threshold
        self._min_liquidity = min_liquidity
        self._min_minutes = min_minutes_to_close

    async def detect(self, events: list[Event]) -> list[NearCertainOpportunity]:
        opportunities: list[NearCertainOpportunity] = []
        for event in events:
            for market in event.tradeable_markets:
                if market.minutes_to_close < self._min_minutes:
                    continue
                if market.liquidity < self._min_liquidity:
                    continue

                sides = [
                    (Side.YES, market.yes_price, market.yes_token_id),
                    (Side.NO, market.no_price, market.no_token_id),
                ]
                for side, price, token_id in sides:
                    if price.value < self._threshold:
                        continue
                    category = MarketCategory.from_string(market.category)
                    fee = self._fee_calc.estimate(
                        price=price,
                        quantity=Decimal("1"),
                        category=category,
                        is_maker=False,
                    )
                    profit_per_share = Decimal("1.0") - price.value - fee.value
                    if profit_per_share <= self._min_profit.value:
                        continue
                    opportunities.append(
                        NearCertainOpportunity(
                            strategy_type="near_certain",
                            market_id=market.id,
                            token_id=token_id.value,
                            event_title=event.title,
                            expected_profit=Money(profit_per_share),
                            entry_price=price.value,
                            side=side,
                            event_slug=event.slug,
                            market_liquidity=market.liquidity,
                            minutes_to_close=market.minutes_to_close,
                            market_end_date=market.end_date,
                            near_certain_price=price.value,
                            expected_return_pct=profit_per_share / price.value * 100,
                        )
                    )
        return opportunities
