from __future__ import annotations
from abc import ABC, abstractmethod
from polymarket_trades.domain.entities.event import Event
from polymarket_trades.domain.value_objects.resolution_outcome import ResolutionOutcome

class EventDiscoveryPort(ABC):
    @abstractmethod
    async def fetch_active_events(self, limit: int, offset: int) -> list[Event]: ...
    @abstractmethod
    async def fetch_event_by_id(self, event_id: str) -> Event: ...
    @abstractmethod
    async def is_market_resolved(self, market_id: str) -> tuple[bool, ResolutionOutcome | None]: ...
