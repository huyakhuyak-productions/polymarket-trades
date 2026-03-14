from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from polymarket_trades.domain.value_objects.price import Price
from polymarket_trades.domain.value_objects.token_id import TokenId

@dataclass(frozen=True)
class OrderbookLevel:
    price: Price
    size: Decimal

@dataclass(frozen=True)
class Orderbook:
    bids: list[OrderbookLevel] = field(default_factory=list)
    asks: list[OrderbookLevel] = field(default_factory=list)

    @property
    def best_bid(self) -> Price | None:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> Price | None:
        return self.asks[0].price if self.asks else None

    @property
    def total_bid_liquidity(self) -> Decimal:
        return sum((level.size for level in self.bids), Decimal("0"))

    @property
    def total_ask_liquidity(self) -> Decimal:
        return sum((level.size for level in self.asks), Decimal("0"))

class PricingPort(ABC):
    @abstractmethod
    async def get_orderbook(self, token_id: TokenId) -> Orderbook: ...
    @abstractmethod
    async def get_best_ask(self, token_id: TokenId) -> Price: ...
    @abstractmethod
    async def get_best_bid(self, token_id: TokenId) -> Price: ...
    @abstractmethod
    async def get_midpoint(self, token_id: TokenId) -> Price: ...
    @abstractmethod
    async def get_fee_rate(self, token_id: TokenId) -> Decimal: ...
