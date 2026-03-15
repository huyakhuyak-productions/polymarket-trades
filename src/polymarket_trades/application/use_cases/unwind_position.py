from __future__ import annotations

import structlog

from polymarket_trades.domain.ports.position_tracker import PositionTrackerPort

logger = structlog.get_logger()


class UnwindPosition:
    """Stub -- logs warning. Full implementation needed before LIVE mode."""

    def __init__(self, position_tracker: PositionTrackerPort) -> None:
        self._pos_tracker = position_tracker

    async def execute(self, position_ids: list[str]) -> None:
        for pid in position_ids:
            logger.warning("unwind_triggered", position_id=pid)
