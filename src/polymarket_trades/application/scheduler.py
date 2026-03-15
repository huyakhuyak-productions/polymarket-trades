from __future__ import annotations

import asyncio
import signal
from decimal import Decimal

import structlog

from polymarket_trades.application.container import Container, build_container, close_container
from polymarket_trades.infrastructure.config.logging import configure_logging
from polymarket_trades.infrastructure.config.settings import Settings

logger = structlog.get_logger()


class Scheduler:
    """Async loop that runs scan -> execute -> reconcile on an interval."""

    def __init__(self, container: Container) -> None:
        self._container = container
        self._running = False

    async def _run_cycle(self) -> None:
        c = self._container

        # 1. Scan for opportunities
        logger.info("cycle_start", phase="scan")
        opportunities = await c.scan_opportunities.execute()

        # 2. Execute trades for viable opportunities
        for opp in opportunities:
            logger.info("cycle_start", phase="execute", market=opp.market_id)
            await c.execute_trade.execute(
                opportunity=opp,
                market_liquidity=opp.market_liquidity,
                minutes_to_close=opp.minutes_to_close,
            )

        # 3. Reconcile open positions
        logger.info("cycle_start", phase="reconcile")
        resolved = await c.reconcile_positions.execute()
        logger.info(
            "cycle_complete",
            opportunities=len(opportunities),
            resolved=resolved,
        )

    async def run(self) -> None:
        self._running = True
        c = self._container
        interval = c.settings.scan_interval_seconds

        # Reconcile orphaned positions on startup
        await c.reconcile_on_startup.execute()

        logger.info(
            "scheduler_started",
            mode=c.settings.trade_mode.value,
            interval_seconds=interval,
        )

        while self._running:
            try:
                await self._run_cycle()
            except Exception:
                logger.exception("cycle_error")

            # Sleep in small increments to allow graceful shutdown
            for _ in range(interval):
                if not self._running:
                    break
                await asyncio.sleep(1)

        logger.info("scheduler_stopped")

    def stop(self) -> None:
        self._running = False


async def run_scheduler(settings: Settings | None = None) -> None:
    """Entry point: build container, wire signals, run scheduler."""
    if settings is None:
        settings = Settings()

    configure_logging(log_level=settings.log_level)

    container = await build_container(settings=settings)
    scheduler = Scheduler(container)

    loop = asyncio.get_running_loop()

    def _handle_signal() -> None:
        logger.info("shutdown_signal_received")
        scheduler.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    try:
        await scheduler.run()
    finally:
        await close_container(container)
