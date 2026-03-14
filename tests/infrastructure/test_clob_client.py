from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock
import pytest
from polymarket_trades.domain.value_objects.token_id import TokenId
from polymarket_trades.infrastructure.api_client.clob_client import ClobClient
from polymarket_trades.infrastructure.api_client.rate_limiter import RateLimiter


def make_sdk() -> MagicMock:
    return MagicMock()


def make_limiter() -> RateLimiter:
    return RateLimiter(requests_per_second=100)


ORDERBOOK_DATA = {
    "asks": [
        {"price": "0.60", "size": "100"},
        {"price": "0.65", "size": "200"},
    ],
    "bids": [
        {"price": "0.55", "size": "150"},
        {"price": "0.50", "size": "300"},
    ],
}


class TestClobClient:
    async def test_get_orderbook_parses_asks_and_bids(self) -> None:
        """get_orderbook should return Orderbook with parsed asks and bids."""
        sdk = make_sdk()
        sdk.get_order_book.return_value = ORDERBOOK_DATA
        client = ClobClient(sdk=sdk, rate_limiter=make_limiter())
        token = TokenId("token-yes-1")
        ob = await client.get_orderbook(token)
        assert len(ob.asks) == 2
        assert len(ob.bids) == 2
        assert ob.best_ask.value == Decimal("0.60")
        assert ob.best_bid.value == Decimal("0.55")
        sdk.get_order_book.assert_called_once_with("token-yes-1")

    async def test_get_best_ask_returns_lowest_ask(self) -> None:
        """get_best_ask should return the lowest ask price from the orderbook."""
        sdk = make_sdk()
        sdk.get_order_book.return_value = ORDERBOOK_DATA
        client = ClobClient(sdk=sdk, rate_limiter=make_limiter())
        token = TokenId("token-yes-1")
        best_ask = await client.get_best_ask(token)
        assert best_ask.value == Decimal("0.60")

    async def test_get_best_bid_returns_highest_bid(self) -> None:
        """get_best_bid should return the highest bid price from the orderbook."""
        sdk = make_sdk()
        sdk.get_order_book.return_value = ORDERBOOK_DATA
        client = ClobClient(sdk=sdk, rate_limiter=make_limiter())
        token = TokenId("token-yes-1")
        best_bid = await client.get_best_bid(token)
        assert best_bid.value == Decimal("0.55")

    async def test_get_midpoint_delegates_to_sdk(self) -> None:
        """get_midpoint should wrap the SDK midpoint result as a Price."""
        sdk = make_sdk()
        sdk.get_midpoint.return_value = 0.575
        client = ClobClient(sdk=sdk, rate_limiter=make_limiter())
        token = TokenId("token-yes-1")
        mid = await client.get_midpoint(token)
        assert mid.value == Decimal("0.575")
        sdk.get_midpoint.assert_called_once_with("token-yes-1")

    async def test_get_best_ask_raises_when_no_asks(self) -> None:
        """get_best_ask should raise ValueError when the orderbook has no asks."""
        sdk = make_sdk()
        sdk.get_order_book.return_value = {"asks": [], "bids": [{"price": "0.50", "size": "100"}]}
        client = ClobClient(sdk=sdk, rate_limiter=make_limiter())
        token = TokenId("token-yes-1")
        with pytest.raises(ValueError, match="No asks"):
            await client.get_best_ask(token)
