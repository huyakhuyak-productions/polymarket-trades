from __future__ import annotations

from polymarket_trades.domain.entities.event import Event
from polymarket_trades.domain.ports.event_discovery import EventDiscoveryPort
from polymarket_trades.domain.value_objects.resolution_outcome import ResolutionOutcome
from polymarket_trades.infrastructure.api_client.gamma_client import GammaClient


class GammaEventDiscovery(EventDiscoveryPort):
    """Adapts GammaClient to the EventDiscoveryPort interface."""

    def __init__(self, client: GammaClient) -> None:
        self._client = client

    async def fetch_active_events(self, limit: int, offset: int) -> list[Event]:
        return await self._client.fetch_events(limit=limit, offset=offset)

    async def fetch_event_by_id(self, event_id: str) -> Event:
        return await self._client.fetch_event_by_id(event_id)

    async def is_market_resolved(self, market_id: str) -> tuple[bool, ResolutionOutcome | None]:
        return await self._client.is_market_resolved(market_id)
