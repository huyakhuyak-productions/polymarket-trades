from __future__ import annotations
from typing import Protocol
from polymarket_trades.domain.entities.event import Event
from polymarket_trades.domain.strategies.opportunity import Opportunity

class DetectorProtocol(Protocol):
    async def detect(self, events: list[Event]) -> list[Opportunity]: ...
