from __future__ import annotations

from decimal import Decimal

from polymarket_trades.domain.ports.pricing import Orderbook, PricingPort
from polymarket_trades.domain.value_objects.price import Price
from polymarket_trades.domain.value_objects.token_id import TokenId
from polymarket_trades.infrastructure.api_client.clob_client import ClobClient


class ClobPricing(PricingPort):
    """Adapts ClobClient to the PricingPort interface."""

    def __init__(self, client: ClobClient) -> None:
        self._client = client

    async def get_orderbook(self, token_id: TokenId) -> Orderbook:
        return await self._client.get_orderbook(token_id)

    async def get_best_ask(self, token_id: TokenId) -> Price:
        return await self._client.get_best_ask(token_id)

    async def get_best_bid(self, token_id: TokenId) -> Price:
        return await self._client.get_best_bid(token_id)

    async def get_midpoint(self, token_id: TokenId) -> Price:
        return await self._client.get_midpoint(token_id)

    async def get_fee_rate(self, token_id: TokenId) -> Decimal:
        return await self._client.get_fee_rate(token_id)
