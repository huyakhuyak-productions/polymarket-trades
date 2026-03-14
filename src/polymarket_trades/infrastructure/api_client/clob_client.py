from __future__ import annotations
import asyncio
from decimal import Decimal
from typing import Any
from polymarket_trades.domain.ports.pricing import Orderbook, OrderbookLevel
from polymarket_trades.domain.ports.trading import Order, OrderId, OrderStatus
from polymarket_trades.domain.value_objects.outcome import Side
from polymarket_trades.domain.value_objects.price import Price
from polymarket_trades.domain.value_objects.token_id import TokenId
from polymarket_trades.domain.value_objects.trade_mode import TimeInForce
from polymarket_trades.infrastructure.api_client.rate_limiter import RateLimiter


class ClobClient:
    def __init__(self, sdk: Any, rate_limiter: RateLimiter) -> None:
        self._sdk = sdk
        self._limiter = rate_limiter

    async def _run(self, func, *args, **kwargs):
        await self._limiter.acquire()
        return await asyncio.to_thread(func, *args, **kwargs)

    async def get_orderbook(self, token_id: TokenId) -> Orderbook:
        data = await self._run(self._sdk.get_order_book, token_id.value)
        asks = [
            OrderbookLevel(price=Price(Decimal(a["price"])), size=Decimal(a["size"]))
            for a in data.get("asks", [])
        ]
        bids = [
            OrderbookLevel(price=Price(Decimal(b["price"])), size=Decimal(b["size"]))
            for b in data.get("bids", [])
        ]
        return Orderbook(asks=asks, bids=bids)

    async def get_best_ask(self, token_id: TokenId) -> Price:
        ob = await self.get_orderbook(token_id)
        if ob.best_ask is None:
            raise ValueError(f"No asks for {token_id.value}")
        return ob.best_ask

    async def get_best_bid(self, token_id: TokenId) -> Price:
        ob = await self.get_orderbook(token_id)
        if ob.best_bid is None:
            raise ValueError(f"No bids for {token_id.value}")
        return ob.best_bid

    async def get_midpoint(self, token_id: TokenId) -> Price:
        mid = await self._run(self._sdk.get_midpoint, token_id.value)
        return Price(Decimal(str(mid)))

    async def get_fee_rate(self, token_id: TokenId) -> Decimal:
        return Decimal("0")

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
        order_args = self._sdk.create_order({
            "token_id": token_id.value,
            "side": "BUY",
            "price": float(price.value),
            "size": float(size),
            "fee_rate_bps": 0,
            "nonce": 0,
            "expiration": 0,
            "tick_size": str(tick_size),
            "neg_risk": neg_risk,
        })
        result = await self._run(self._sdk.post_order, order_args, time_in_force.value)
        return OrderId(value=result.get("orderID", result.get("id", "")))

    async def cancel_order(self, order_id: OrderId) -> bool:
        result = await self._run(self._sdk.cancel, order_id.value)
        return result is not None

    async def get_order_status(self, order_id: OrderId) -> OrderStatus:
        result = await self._run(self._sdk.get_order, order_id.value)
        status_map = {
            "LIVE": OrderStatus.PENDING,
            "FILLED": OrderStatus.FILLED,
            "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
            "CANCELLED": OrderStatus.CANCELLED,
            "EXPIRED": OrderStatus.EXPIRED,
        }
        return status_map.get(result.get("status", ""), OrderStatus.PENDING)

    async def get_open_orders(self) -> list[Order]:
        result = await self._run(self._sdk.get_orders)
        return [
            Order(
                id=OrderId(o["id"]),
                token_id=TokenId(o["asset_id"]),
                side=Side.YES if o["side"] == "BUY" else Side.NO,
                price=Price(Decimal(o["price"])),
                size=Decimal(o["original_size"]),
                filled_size=Decimal(o.get("size_matched", "0")),
                status=OrderStatus.PENDING,
                time_in_force=TimeInForce.GTC,
            )
            for o in result
        ]
