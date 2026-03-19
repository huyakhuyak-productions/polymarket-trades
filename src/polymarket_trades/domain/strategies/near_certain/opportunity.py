from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from polymarket_trades.domain.strategies.opportunity import Opportunity


@dataclass
class NearCertainOpportunity(Opportunity):
    near_certain_price: Decimal = Decimal("0")
    expected_return_pct: Decimal = Decimal("0")
