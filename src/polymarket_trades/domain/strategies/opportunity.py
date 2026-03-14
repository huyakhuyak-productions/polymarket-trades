from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from polymarket_trades.domain.value_objects.money import Money

@dataclass
class Opportunity:
    """Base class for all strategy-detected opportunities."""
    strategy_type: str
    market_id: str
    token_id: str
    event_title: str
    expected_profit: Money
    entry_price: Decimal
    market_liquidity: Decimal = Decimal("0")
    minutes_to_close: float = 0.0
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
