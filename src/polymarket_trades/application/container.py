from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import aiosqlite

from polymarket_trades.application.use_cases.execute_trade import ExecuteTrade
from polymarket_trades.application.use_cases.monitor_positions import MonitorPositions
from polymarket_trades.application.use_cases.reconcile_on_startup import ReconcileOnStartup
from polymarket_trades.application.use_cases.reconcile_positions import ReconcilePositions
from polymarket_trades.application.use_cases.scan_opportunities import ScanOpportunities
from polymarket_trades.application.use_cases.unwind_position import UnwindPosition
from polymarket_trades.domain.ports.event_discovery import EventDiscoveryPort
from polymarket_trades.domain.ports.pricing import PricingPort
from polymarket_trades.domain.services.fee_calculator import FeeCalculator
from polymarket_trades.domain.services.risk_manager import RiskConfig, RiskManager
from polymarket_trades.domain.services.scanner import Scanner
from polymarket_trades.domain.strategies.arbitrage.detector import ArbitrageDetector
from polymarket_trades.domain.strategies.near_certain.detector import NearCertainDetector
from polymarket_trades.domain.strategies.neg_risk_discount.detector import NegRiskDiscountDetector
from polymarket_trades.infrastructure.adapters.clob_pricing import ClobPricing
from polymarket_trades.infrastructure.adapters.gamma_event_discovery import GammaEventDiscovery
from polymarket_trades.infrastructure.api_client.clob_client import ClobClient
from polymarket_trades.infrastructure.api_client.gamma_client import GammaClient
from polymarket_trades.infrastructure.api_client.rate_limiter import RateLimiter
from polymarket_trades.infrastructure.config.settings import Settings
from polymarket_trades.infrastructure.persistence.migrator import run_migrations
from polymarket_trades.infrastructure.persistence.sqlite_opportunity_store import (
    SqliteOpportunityStore,
)
from polymarket_trades.infrastructure.persistence.sqlite_position_tracker import (
    SqlitePositionTracker,
)
from polymarket_trades.domain.value_objects.money import Money
from polymarket_trades.domain.value_objects.trade_mode import TradeMode


@dataclass
class Container:
    """Dependency injection container wiring all layers together."""

    db: aiosqlite.Connection
    event_discovery: EventDiscoveryPort
    pricing: PricingPort | None
    opportunity_store: SqliteOpportunityStore
    position_tracker: SqlitePositionTracker
    scanner: Scanner
    risk_manager: RiskManager
    fee_calculator: FeeCalculator
    scan_opportunities: ScanOpportunities
    execute_trade: ExecuteTrade
    reconcile_positions: ReconcilePositions
    reconcile_on_startup: ReconcileOnStartup
    monitor_positions: MonitorPositions
    unwind_position: UnwindPosition
    settings: Settings

    # Optional clients to close on shutdown
    _gamma_client: GammaClient | None = None


async def build_container(
    settings: Settings | None = None,
    db_path: str = "polymarket_trades.db",
) -> Container:
    """Build and wire all dependencies."""
    if settings is None:
        settings = Settings()

    # Database
    db = await aiosqlite.connect(db_path)
    await run_migrations(db)

    # Infrastructure: API clients
    rate_limiter = RateLimiter(settings.rate_limit_requests_per_second)
    gamma_client = GammaClient(
        base_url=settings.gamma_base_url, rate_limiter=rate_limiter
    )
    event_discovery = GammaEventDiscovery(gamma_client)

    # Pricing: only available when private key is set (CLOB SDK needs it)
    pricing: PricingPort | None = None
    if settings.polymarket_private_key:
        try:
            from py_clob_client.client import ClobClient as SdkClient

            sdk = SdkClient(
                settings.clob_base_url,
                key=settings.polymarket_private_key,
                chain_id=137,
            )
            clob_client = ClobClient(sdk=sdk, rate_limiter=rate_limiter)
            pricing = ClobPricing(clob_client)
        except Exception:
            pricing = None

    # Domain services
    fee_calculator = FeeCalculator(
        crypto_fee_rate=settings.crypto_fee_rate,
        sports_fee_rate=settings.sports_fee_rate,
    )

    detectors = [
        NearCertainDetector(
            fee_calculator=fee_calculator,
            price_threshold=settings.near_certain_threshold,
            min_profit_threshold=Money(settings.min_profit_threshold),
            min_liquidity=settings.min_market_liquidity,
            min_minutes_to_close=settings.min_minutes_to_close,
        ),
        ArbitrageDetector(
            fee_calculator=fee_calculator,
            min_profit_threshold=Money(settings.min_profit_threshold),
        ),
        NegRiskDiscountDetector(
            fee_calculator=fee_calculator,
            min_profit_threshold=Money(settings.min_profit_threshold),
            min_liquidity_per_outcome=settings.min_market_liquidity,
        ),
    ]
    scanner = Scanner(detectors=detectors)

    risk_config = RiskConfig(
        total_capital=settings.total_capital,
        max_single_position_pct=settings.max_single_position_pct,
        max_total_exposure_pct=settings.max_total_exposure_pct,
        min_profit_threshold=Money(settings.min_profit_threshold),
        min_minutes_to_close=settings.min_minutes_to_close,
        min_market_liquidity=settings.min_market_liquidity,
    )
    risk_manager = RiskManager(risk_config)

    # Persistence
    opportunity_store = SqliteOpportunityStore(db)
    position_tracker = SqlitePositionTracker(db)

    # Use cases
    scan_opportunities = ScanOpportunities(
        event_discovery=event_discovery,
        scanner=scanner,
        opportunity_store=opportunity_store,
        position_tracker=position_tracker,
        page_size=settings.gamma_page_size,
    )

    execute_trade = ExecuteTrade(
        position_tracker=position_tracker,
        pricing=pricing,
        risk_manager=risk_manager,
        fee_calculator=fee_calculator,
        mode=settings.trade_mode,
    )

    reconcile_positions = ReconcilePositions(
        position_tracker=position_tracker,
        event_discovery=event_discovery,
        pricing=pricing,
    )

    reconcile_on_startup = ReconcileOnStartup(
        position_tracker=position_tracker,
    )

    monitor_positions = MonitorPositions(
        position_tracker=position_tracker,
    )

    unwind_position = UnwindPosition(
        position_tracker=position_tracker,
    )

    return Container(
        db=db,
        event_discovery=event_discovery,
        pricing=pricing,
        opportunity_store=opportunity_store,
        position_tracker=position_tracker,
        scanner=scanner,
        risk_manager=risk_manager,
        fee_calculator=fee_calculator,
        scan_opportunities=scan_opportunities,
        execute_trade=execute_trade,
        reconcile_positions=reconcile_positions,
        reconcile_on_startup=reconcile_on_startup,
        monitor_positions=monitor_positions,
        unwind_position=unwind_position,
        settings=settings,
        _gamma_client=gamma_client,
    )


async def close_container(container: Container) -> None:
    """Gracefully close all resources."""
    if container._gamma_client:
        await container._gamma_client.close()
    await container.db.close()
