from __future__ import annotations

from decimal import Decimal

from polymarket_trades.domain.ports.trading import Order, OrderId, OrderStatus, TradingPort
from polymarket_trades.domain.value_objects.outcome import Side
from polymarket_trades.domain.value_objects.price import Price
from polymarket_trades.domain.value_objects.token_id import TokenId
from polymarket_trades.domain.value_objects.trade_mode import TimeInForce
from polymarket_trades.infrastructure.api_client.clob_client import ClobClient


class ClobTrading(TradingPort):
    """Adapts ClobClient to the TradingPort interface."""

    def __init__(self, client: ClobClient) -> None:
        self._client = client

    async def place_order(
        self,
        token_id: TokenId,
        side: Side,
        price: Price,
        size: Decimal,
        time_in_force: TimeInForce,
        tick_size: Decimal,
        neg_risk: bool,
    ) -> OrderId:
        return await self._client.place_order(
            token_id=token_id,
            side=side,
            price=price,
            size=size,
            time_in_force=time_in_force,
            tick_size=tick_size,
            neg_risk=neg_risk,
        )

    async def cancel_order(self, order_id: OrderId) -> bool:
        return await self._client.cancel_order(order_id)

    async def get_order_status(self, order_id: OrderId) -> OrderStatus:
        return await self._client.get_order_status(order_id)

    async def get_open_orders(self) -> list[Order]:
        return await self._client.get_open_orders()
