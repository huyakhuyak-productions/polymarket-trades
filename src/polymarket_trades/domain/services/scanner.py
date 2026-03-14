from __future__ import annotations
import asyncio
from polymarket_trades.domain.entities.event import Event
from polymarket_trades.domain.strategies.detector_protocol import DetectorProtocol
from polymarket_trades.domain.strategies.opportunity import Opportunity

class Scanner:
    def __init__(self, detectors: list[DetectorProtocol]) -> None:
        self._detectors = detectors

    async def scan(self, events: list[Event]) -> list[Opportunity]:
        if not self._detectors:
            return []
        results = await asyncio.gather(*(d.detect(events) for d in self._detectors))
        return [opp for batch in results for opp in batch]
