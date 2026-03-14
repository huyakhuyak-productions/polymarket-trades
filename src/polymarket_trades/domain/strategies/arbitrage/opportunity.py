from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from polymarket_trades.domain.strategies.opportunity import Opportunity


@dataclass
class ArbitrageOpportunity(Opportunity):
    no_token_id: str = ""  # IMPORTANT: needed for placing the NO-side order
    yes_ask: Decimal = Decimal("0")
    no_ask: Decimal = Decimal("0")
    spread: Decimal = Decimal("0")
