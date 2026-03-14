from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from polymarket_trades.domain.value_objects.outcome import Outcome, Side
from polymarket_trades.domain.value_objects.price import Price
from polymarket_trades.domain.value_objects.token_id import TokenId


@dataclass
class Market:
    id: str
    question: str
    condition_id: str
    slug: str
    yes_token_id: TokenId
    no_token_id: TokenId
    yes_price: Price
    no_price: Price
    liquidity: Decimal
    volume: Decimal
    enable_order_book: bool
    tick_size: Decimal
    neg_risk: bool
    end_date: datetime | None
    closed: bool
    category: str

    @property
    def is_tradeable(self) -> bool:
        return self.enable_order_book and not self.closed

    @property
    def minutes_to_close(self) -> float:
        if self.end_date is None:
            return float("inf")
        delta = self.end_date - datetime.now(timezone.utc)
        return delta.total_seconds() / 60

    @property
    def outcomes(self) -> list[Outcome]:
        return [
            Outcome(side=Side.YES, price=self.yes_price),
            Outcome(side=Side.NO, price=self.no_price),
        ]
