from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import structlog

from polymarket_trades.domain.entities.position import Position
from polymarket_trades.domain.ports.position_tracker import PositionTrackerPort
from polymarket_trades.domain.ports.pricing import PricingPort
from polymarket_trades.domain.services.fee_calculator import FeeCalculator, MarketCategory
from polymarket_trades.domain.services.risk_manager import RiskManager
from polymarket_trades.domain.strategies.opportunity import Opportunity
from polymarket_trades.domain.value_objects.outcome import Side
from polymarket_trades.domain.value_objects.price import Price
from polymarket_trades.domain.value_objects.token_id import TokenId
from polymarket_trades.domain.value_objects.trade_mode import PositionStatus, TradeMode

logger = structlog.get_logger()


class ExecuteTrade:
    def __init__(
        self,
        position_tracker: PositionTrackerPort,
        pricing: PricingPort | None,
        risk_manager: RiskManager,
        fee_calculator: FeeCalculator,
        mode: TradeMode,
    ) -> None:
        self._pos_tracker = position_tracker
        self._pricing = pricing
        self._risk_mgr = risk_manager
        self._fee_calc = fee_calculator
        self._mode = mode

    async def execute(
        self,
        opportunity: Opportunity,
        market_liquidity: Decimal,
        minutes_to_close: float,
    ) -> bool:
        if self._pricing:
            try:
                fresh_price = await self._pricing.get_best_ask(
                    TokenId(opportunity.token_id)
                )
                if fresh_price.value != opportunity.entry_price:
                    logger.info(
                        "price_moved",
                        market=opportunity.market_id,
                        old=str(opportunity.entry_price),
                        new=str(fresh_price.value),
                    )
                    opportunity.entry_price = fresh_price.value
            except Exception:
                logger.warning(
                    "price_revalidation_failed", market=opportunity.market_id
                )

        current_positions = await self._pos_tracker.get_open_positions()
        decision = self._risk_mgr.evaluate(
            opportunity=opportunity,
            current_positions=current_positions,
            market_liquidity=market_liquidity,
            minutes_to_close=minutes_to_close,
        )
        if not decision.approved:
            logger.info(
                "trade_rejected",
                reason=decision.reason,
                market=opportunity.market_id,
            )
            return False

        category = MarketCategory.FEE_EXEMPT
        fees = self._fee_calc.estimate(
            price=Price(opportunity.entry_price),
            quantity=decision.max_quantity,
            category=category,
            is_maker=False,
        )

        now = datetime.now(timezone.utc)
        position = Position(
            id=uuid.uuid4(),
            opportunity_type=opportunity.strategy_type,
            market_id=opportunity.market_id,
            token_id=TokenId(opportunity.token_id),
            side=Side.YES,
            event_title=opportunity.event_title,
            event_slug=opportunity.event_slug,
            entry_price=opportunity.entry_price,
            quantity=decision.max_quantity,
            detected_at=opportunity.detected_at,
            entry_time=now,
            current_price=opportunity.entry_price,
            resolution_outcome=None,
            exit_price=None,
            pnl=None,
            fees_estimated=fees.value,
            mode=self._mode,
            status=PositionStatus.ENTERED,
        )
        await self._pos_tracker.save_position(position)
        logger.info(
            "trade_executed",
            mode=self._mode.value,
            market=opportunity.market_id,
            price=str(opportunity.entry_price),
            quantity=str(decision.max_quantity),
        )
        return True
