from __future__ import annotations
import json
from datetime import datetime, timezone
from decimal import Decimal
import httpx
from polymarket_trades.domain.entities.event import Event
from polymarket_trades.domain.entities.market import Market
from polymarket_trades.domain.value_objects.price import Price
from polymarket_trades.domain.value_objects.resolution_outcome import ResolutionOutcome
from polymarket_trades.domain.value_objects.token_id import TokenId
from polymarket_trades.infrastructure.api_client.rate_limiter import RateLimiter


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def _parse_list_field(value: str | list | None) -> list:
    """Gamma API returns some list fields as JSON strings."""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return []
    return value


def _clamp_price(value: Decimal) -> Decimal:
    """Clamp to [0, 1] — API can return extreme precision values."""
    return max(Decimal("0"), min(Decimal("1"), value))


def _parse_market(data: dict) -> Market:
    clob_ids = _parse_list_field(data.get("clobTokenIds"))
    prices = _parse_list_field(data.get("outcomePrices"))
    yes_token = clob_ids[0] if len(clob_ids) > 0 else ""
    no_token = clob_ids[1] if len(clob_ids) > 1 else ""
    yes_price = _clamp_price(Decimal(prices[0])) if len(prices) > 0 else Decimal("0")
    no_price = _clamp_price(Decimal(prices[1])) if len(prices) > 1 else Decimal("0")
    return Market(
        id=data["id"],
        question=data.get("question", ""),
        condition_id=data.get("conditionId", ""),
        slug=data.get("slug", ""),
        yes_token_id=TokenId(yes_token) if yes_token else TokenId("unknown"),
        no_token_id=TokenId(no_token) if no_token else TokenId("unknown"),
        yes_price=Price(yes_price),
        no_price=Price(no_price),
        liquidity=Decimal(data.get("liquidity", "0") or "0"),
        volume=Decimal(data.get("volume", "0") or "0"),
        enable_order_book=data.get("enableOrderBook", False),
        tick_size=Decimal(data.get("tickSize", "0.01") or "0.01"),
        neg_risk=data.get("negRisk", False),
        end_date=_parse_datetime(data.get("endDate")),
        closed=data.get("closed", False),
        category=data.get("category", ""),
    )


def _parse_event(data: dict) -> Event:
    markets = [_parse_market(m) for m in data.get("markets", [])]
    return Event(
        id=str(data["id"]),
        title=data.get("title", ""),
        slug=data.get("slug", ""),
        description=data.get("description", ""),
        start_date=_parse_datetime(data.get("startDate")),
        end_date=_parse_datetime(data.get("endDate")),
        active=data.get("active", False),
        closed=data.get("closed", False),
        archived=data.get("archived", False),
        liquidity=Decimal(data.get("liquidity", "0") or "0"),
        volume=Decimal(data.get("volume", "0") or "0"),
        neg_risk=data.get("enableNegRisk", data.get("negRisk", False)),
        markets=markets,
        category=data.get("category", ""),
    )


class GammaClient:
    def __init__(self, base_url: str, rate_limiter: RateLimiter) -> None:
        self._base_url = base_url.rstrip("/")
        self._limiter = rate_limiter
        self._client = httpx.AsyncClient(timeout=30.0)

    async def fetch_events(
        self, limit: int, offset: int, min_liquidity: float = 100.0
    ) -> list[Event]:
        await self._limiter.acquire()
        resp = await self._client.get(
            f"{self._base_url}/events",
            params={
                "limit": limit,
                "offset": offset,
                "active": True,
                "liquidity_min": min_liquidity,
                "order": "liquidity",
                "ascending": False,
            },
        )
        resp.raise_for_status()
        return [_parse_event(e) for e in resp.json()]

    async def fetch_event_by_id(self, event_id: str) -> Event:
        await self._limiter.acquire()
        resp = await self._client.get(f"{self._base_url}/events/{event_id}")
        resp.raise_for_status()
        return _parse_event(resp.json())

    async def fetch_event_slug_for_market(self, market_id: str) -> str:
        """Look up the parent event slug for a given market ID.

        Uses the list endpoint (/markets?id=X) because the single-market
        endpoint (/markets/X) does not embed the parent event.
        """
        await self._limiter.acquire()
        resp = await self._client.get(
            f"{self._base_url}/markets", params={"id": market_id}
        )
        resp.raise_for_status()
        results = resp.json()
        if results and isinstance(results, list) and len(results) > 0:
            events = results[0].get("events", [])
            if events and isinstance(events, list):
                return events[0].get("slug", "")
        return ""

    async def is_market_resolved(self, market_id: str) -> tuple[bool, ResolutionOutcome | None]:
        await self._limiter.acquire()
        resp = await self._client.get(f"{self._base_url}/markets/{market_id}")
        resp.raise_for_status()
        data = resp.json()
        if not data.get("closed", False):
            return False, None
        prices = _parse_list_field(data.get("outcomePrices"))
        if len(prices) >= 2:
            if Decimal(prices[0]) >= Decimal("0.99"):
                return True, ResolutionOutcome.YES
            if Decimal(prices[1]) >= Decimal("0.99"):
                return True, ResolutionOutcome.NO
            return False, None
        return True, ResolutionOutcome.INVALID

    async def close(self) -> None:
        await self._client.aclose()
