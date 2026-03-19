from __future__ import annotations

import structlog

from polymarket_trades.domain.ports.event_discovery import EventDiscoveryPort
from polymarket_trades.domain.ports.opportunity_store import OpportunityStorePort
from polymarket_trades.domain.ports.position_tracker import PositionTrackerPort
from polymarket_trades.domain.services.scanner import Scanner
from polymarket_trades.domain.strategies.opportunity import Opportunity

logger = structlog.get_logger()


class ScanOpportunities:
    def __init__(
        self,
        event_discovery: EventDiscoveryPort,
        scanner: Scanner,
        opportunity_store: OpportunityStorePort,
        position_tracker: PositionTrackerPort,
        page_size: int = 100,
        max_pages: int = 10,
    ) -> None:
        self._events = event_discovery
        self._scanner = scanner
        self._opp_store = opportunity_store
        self._pos_tracker = position_tracker
        self._page_size = page_size
        self._max_pages = max_pages

    async def execute(self) -> list[Opportunity]:
        all_events = []
        offset = 0
        pages_fetched = 0
        while pages_fetched < self._max_pages:
            page = await self._events.fetch_active_events(
                limit=self._page_size, offset=offset
            )
            if not page:
                break
            all_events.extend(page)
            offset += self._page_size
            pages_fetched += 1

        logger.info("events_fetched", count=len(all_events))
        raw_opps = await self._scanner.scan(all_events)
        logger.info("opportunities_detected", count=len(raw_opps))

        viable = []
        for opp in raw_opps:
            existing = await self._opp_store.find_existing(
                opp.strategy_type, opp.market_id, opp.token_id
            )
            if existing:
                continue
            pos = await self._pos_tracker.get_position_by_market(opp.market_id)
            if pos and pos.is_open:
                continue
            await self._opp_store.save(opp)
            viable.append(opp)

        viable.sort(key=lambda opp: opp.sort_key)
        logger.info("opportunities_viable", count=len(viable))
        return viable
