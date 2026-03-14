from __future__ import annotations
from decimal import Decimal
from polymarket_trades.domain.entities.event import Event
from polymarket_trades.domain.services.fee_calculator import FeeCalculator, MarketCategory
from polymarket_trades.domain.strategies.neg_risk_discount.opportunity import NegRiskOpportunity
from polymarket_trades.domain.value_objects.money import Money


class NegRiskDiscountDetector:
    def __init__(
        self,
        fee_calculator: FeeCalculator,
        min_profit_threshold: Money = Money(Decimal("0.001")),
        min_liquidity_per_outcome: Decimal = Decimal("100"),
    ) -> None:
        self._fee_calc = fee_calculator
        self._min_profit = min_profit_threshold
        self._min_liquidity = min_liquidity_per_outcome

    async def detect(self, events: list[Event]) -> list[NegRiskOpportunity]:
        opportunities: list[NegRiskOpportunity] = []
        for event in events:
            if not event.is_multi_outcome:
                continue
            tradeable = event.tradeable_markets
            if len(tradeable) != len(event.markets):  # ALL must be tradeable
                continue
            if any(m.liquidity < self._min_liquidity for m in tradeable):
                continue
            total_cost = sum((m.yes_price.value for m in tradeable), Decimal("0"))
            if total_cost >= Decimal("1.0"):
                continue
            total_fees = Decimal("0")
            for m in tradeable:
                category = MarketCategory.from_string(m.category)
                fee = self._fee_calc.estimate(
                    price=m.yes_price,
                    quantity=Decimal("1"),
                    category=category,
                    is_maker=False,
                )
                total_fees += fee.value
            profit_per_unit = Decimal("1.0") - total_cost - total_fees
            if profit_per_unit <= self._min_profit.value:
                continue
            opportunities.append(
                NegRiskOpportunity(
                    strategy_type="neg_risk_discount",
                    market_id=event.id,
                    token_id=tradeable[0].yes_token_id.value,
                    event_title=event.title,
                    expected_profit=Money(profit_per_unit),
                    entry_price=total_cost,
                    total_cost=total_cost,
                    num_outcomes=len(tradeable),
                    leg_token_ids=[m.yes_token_id.value for m in tradeable],
                    leg_prices=[m.yes_price.value for m in tradeable],
                )
            )
        return opportunities
