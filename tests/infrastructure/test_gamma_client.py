from __future__ import annotations

import json
import pytest
import respx
import httpx
from polymarket_trades.domain.value_objects.resolution_outcome import ResolutionOutcome
from polymarket_trades.infrastructure.api_client.gamma_client import GammaClient
from polymarket_trades.infrastructure.api_client.rate_limiter import RateLimiter

BASE_URL = "https://gamma-api.polymarket.com"


def make_limiter() -> RateLimiter:
    return RateLimiter(requests_per_second=100)


SAMPLE_MARKET = {
    "id": "market-1",
    "question": "Will X happen?",
    "conditionId": "cond-1",
    "slug": "will-x-happen",
    "clobTokenIds": ["token-yes-1", "token-no-1"],
    "outcomePrices": ["0.65", "0.35"],
    "liquidity": "1000.00",
    "volume": "5000.00",
    "enableOrderBook": True,
    "tickSize": "0.01",
    "negRisk": False,
    "endDate": "2026-06-01T00:00:00Z",
    "closed": False,
    "category": "sports",
}

SAMPLE_EVENT = {
    "id": "event-1",
    "title": "Test Event",
    "slug": "test-event",
    "description": "A test event",
    "startDate": "2026-01-01T00:00:00Z",
    "endDate": "2026-06-01T00:00:00Z",
    "active": True,
    "closed": False,
    "archived": False,
    "liquidity": "10000.00",
    "volume": "50000.00",
    "negRisk": False,
    "category": "sports",
    "markets": [SAMPLE_MARKET],
}


class TestGammaClientFetchEvents:
    @respx.mock
    async def test_fetch_events_returns_single_page(self) -> None:
        """fetch_events should parse events from the API response."""
        respx.get(f"{BASE_URL}/events").mock(
            return_value=httpx.Response(200, json=[SAMPLE_EVENT])
        )
        client = GammaClient(base_url=BASE_URL, rate_limiter=make_limiter())
        try:
            events = await client.fetch_events(limit=10, offset=0)
        finally:
            await client.close()
        assert len(events) == 1
        event = events[0]
        assert event.id == "event-1"
        assert event.title == "Test Event"
        assert event.active is True
        assert len(event.markets) == 1
        market = event.markets[0]
        assert market.id == "market-1"
        assert str(market.yes_price.value) == "0.65"

    @respx.mock
    async def test_fetch_events_returns_empty_list(self) -> None:
        """fetch_events should handle empty API response gracefully."""
        respx.get(f"{BASE_URL}/events").mock(
            return_value=httpx.Response(200, json=[])
        )
        client = GammaClient(base_url=BASE_URL, rate_limiter=make_limiter())
        try:
            events = await client.fetch_events(limit=10, offset=0)
        finally:
            await client.close()
        assert events == []

    @respx.mock
    async def test_fetch_event_by_id_parses_markets(self) -> None:
        """fetch_event_by_id should parse event with embedded markets."""
        respx.get(f"{BASE_URL}/events/event-1").mock(
            return_value=httpx.Response(200, json=SAMPLE_EVENT)
        )
        client = GammaClient(base_url=BASE_URL, rate_limiter=make_limiter())
        try:
            event = await client.fetch_event_by_id("event-1")
        finally:
            await client.close()
        assert event.id == "event-1"
        assert len(event.markets) == 1
        market = event.markets[0]
        assert market.yes_token_id.value == "token-yes-1"
        assert market.no_token_id.value == "token-no-1"
        assert market.enable_order_book is True
        assert market.closed is False

    @respx.mock
    async def test_is_market_resolved_detects_yes_resolution(self) -> None:
        """is_market_resolved should return (True, YES) when YES price >= 0.99."""
        resolved_market = {
            "id": "market-1",
            "closed": True,
            "outcomePrices": ["0.99", "0.01"],
        }
        respx.get(f"{BASE_URL}/markets/market-1").mock(
            return_value=httpx.Response(200, json=resolved_market)
        )
        client = GammaClient(base_url=BASE_URL, rate_limiter=make_limiter())
        try:
            resolved, outcome = await client.is_market_resolved("market-1")
        finally:
            await client.close()
        assert resolved is True
        assert outcome == ResolutionOutcome.YES

    @respx.mock
    async def test_is_market_resolved_returns_false_for_open_market(self) -> None:
        """is_market_resolved should return (False, None) for an open market."""
        open_market = {
            "id": "market-2",
            "closed": False,
            "outcomePrices": ["0.55", "0.45"],
        }
        respx.get(f"{BASE_URL}/markets/market-2").mock(
            return_value=httpx.Response(200, json=open_market)
        )
        client = GammaClient(base_url=BASE_URL, rate_limiter=make_limiter())
        try:
            resolved, outcome = await client.is_market_resolved("market-2")
        finally:
            await client.close()
        assert resolved is False
        assert outcome is None
