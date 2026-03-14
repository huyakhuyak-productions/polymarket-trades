from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from polymarket_trades.domain.entities.market import Market


@dataclass
class Event:
    id: str
    title: str
    slug: str
    description: str
    start_date: datetime | None
    end_date: datetime | None
    active: bool
    closed: bool
    archived: bool
    liquidity: Decimal
    volume: Decimal
    neg_risk: bool
    markets: list[Market] = field(default_factory=list)
    category: str = ""

    @property
    def tradeable_markets(self) -> list[Market]:
        return [m for m in self.markets if m.is_tradeable]

    @property
    def is_multi_outcome(self) -> bool:
        return self.neg_risk and len(self.markets) >= 3
