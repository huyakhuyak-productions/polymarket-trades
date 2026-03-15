from __future__ import annotations

import structlog

from polymarket_trades.domain.ports.position_tracker import PositionTrackerPort
from polymarket_trades.domain.value_objects.trade_mode import PositionStatus

logger = structlog.get_logger()


class ReconcileOnStartup:
    def __init__(self, position_tracker: PositionTrackerPort) -> None:
        self._pos_tracker = position_tracker

    async def execute(self) -> None:
        open_positions = await self._pos_tracker.get_open_positions()
        entered = [p for p in open_positions if p.status == PositionStatus.ENTERED]
        if entered:
            logger.warning("orphaned_positions_found", count=len(entered))
            for pos in entered:
                pos.status = PositionStatus.MONITORING
                await self._pos_tracker.update_position(pos)
            logger.info("orphaned_positions_recovered", count=len(entered))
