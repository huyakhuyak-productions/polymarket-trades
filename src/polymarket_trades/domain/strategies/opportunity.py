from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from polymarket_trades.domain.value_objects.money import Money
from polymarket_trades.domain.value_objects.outcome import Side

@dataclass
class Opportunity:
    """Base class for all strategy-detected opportunities."""
    strategy_type: str
    market_id: str
    token_id: str
    event_title: str
    expected_profit: Money
    entry_price: Decimal
    side: Side = Side.YES
    event_slug: str = ""
    market_liquidity: Decimal = Decimal("0")
    minutes_to_close: float = 0.0
    market_end_date: datetime | None = None
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def sort_key(self) -> tuple[float, float]:
        """(minutes_to_close ASC, return_pct DESC) for capital-rotation priority."""
        if self.entry_price == 0:
            return_pct = float("inf")
        else:
            return_pct = float(self.expected_profit.value / self.entry_price)
        return (self.minutes_to_close, -return_pct)
