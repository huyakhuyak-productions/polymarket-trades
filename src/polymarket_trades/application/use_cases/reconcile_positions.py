from __future__ import annotations

import structlog

from polymarket_trades.domain.ports.event_discovery import EventDiscoveryPort
from polymarket_trades.domain.ports.position_tracker import PositionTrackerPort
from polymarket_trades.domain.ports.pricing import PricingPort
from polymarket_trades.domain.value_objects.token_id import TokenId

logger = structlog.get_logger()


class ReconcilePositions:
    def __init__(
        self,
        position_tracker: PositionTrackerPort,
        event_discovery: EventDiscoveryPort,
        pricing: PricingPort | None,
    ) -> None:
        self._pos_tracker = position_tracker
        self._events = event_discovery
        self._pricing = pricing

    async def execute(self) -> int:
        open_positions = await self._pos_tracker.get_open_positions()
        resolved_count = 0
        for pos in open_positions:
            if self._pricing:
                try:
                    current_price = await self._pricing.get_midpoint(
                        TokenId(pos.token_id.value)
                    )
                    pos.current_price = current_price.value
                except Exception:
                    logger.warning("price_update_failed", market=pos.market_id)

            is_resolved, outcome = await self._events.is_market_resolved(
                pos.market_id
            )
            if is_resolved and outcome:
                pos.resolve(outcome)
                resolved_count += 1
                logger.info(
                    "position_resolved",
                    market=pos.market_id,
                    outcome=outcome.value,
                    pnl=str(pos.pnl),
                )
            await self._pos_tracker.update_position(pos)

        return resolved_count
