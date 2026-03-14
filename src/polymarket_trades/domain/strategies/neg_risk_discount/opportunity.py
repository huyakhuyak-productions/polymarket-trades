from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from polymarket_trades.domain.strategies.opportunity import Opportunity


@dataclass
class NegRiskOpportunity(Opportunity):
    total_cost: Decimal = Decimal("0")
    num_outcomes: int = 0
    leg_token_ids: list[str] = field(default_factory=list)
    leg_prices: list[Decimal] = field(default_factory=list)
