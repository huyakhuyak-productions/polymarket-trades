from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from polymarket_trades.domain.value_objects.outcome import Side
from polymarket_trades.domain.value_objects.price import Price
from polymarket_trades.domain.value_objects.token_id import TokenId
from polymarket_trades.domain.value_objects.trade_mode import TimeInForce

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

@dataclass(frozen=True)
class OrderId:
    value: str

@dataclass
class Order:
    id: OrderId
    token_id: TokenId
    side: Side
    price: Price
    size: Decimal
    filled_size: Decimal
    status: OrderStatus
    time_in_force: TimeInForce

class TradingPort(ABC):
    @abstractmethod
    async def place_order(self, token_id: TokenId, side: Side, price: Price, size: Decimal, time_in_force: TimeInForce, tick_size: Decimal, neg_risk: bool) -> OrderId: ...
    @abstractmethod
    async def cancel_order(self, order_id: OrderId) -> bool: ...
    @abstractmethod
    async def get_order_status(self, order_id: OrderId) -> OrderStatus: ...
    @abstractmethod
    async def get_open_orders(self) -> list[Order]: ...
