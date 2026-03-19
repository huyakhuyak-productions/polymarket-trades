from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from polymarket_trades.application.use_cases.execute_trade import ExecuteTrade
from polymarket_trades.domain.services.fee_calculator import FeeCalculator
from polymarket_trades.domain.services.risk_manager import RiskConfig, RiskDecision, RiskManager
from polymarket_trades.domain.strategies.opportunity import Opportunity
from polymarket_trades.domain.value_objects.money import Money
from polymarket_trades.domain.value_objects.outcome import Side
from polymarket_trades.domain.value_objects.price import Price
from polymarket_trades.domain.value_objects.token_id import TokenId
from polymarket_trades.domain.value_objects.trade_mode import PositionStatus, TradeMode


def _make_opportunity(
    entry_price: Decimal = Decimal("0.96"),
    side: Side = Side.YES,
) -> Opportunity:
    return Opportunity(
        strategy_type="near_certain",
        market_id="m1",
        token_id="0xyes" if side == Side.YES else "0xno",
        event_title="Test",
        expected_profit=Money(Decimal("2.00")),
        entry_price=entry_price,
        side=side,
    )


def _make_risk_config() -> RiskConfig:
    return RiskConfig(
        total_capital=Decimal("1000"),
        max_single_position_pct=Decimal("0.20"),
        max_total_exposure_pct=Decimal("0.80"),
        min_profit_threshold=Money(Decimal("0.005")),
        min_minutes_to_close=60,
        min_market_liquidity=Decimal("100"),
    )


class TestExecuteTrade:
    @pytest.mark.asyncio
    async def test_paper_mode_records_position(self):
        pos_tracker = AsyncMock()
        pos_tracker.get_open_positions.return_value = []

        risk_mgr = RiskManager(_make_risk_config())
        fee_calc = FeeCalculator()

        uc = ExecuteTrade(
            position_tracker=pos_tracker,
            pricing=None,
            risk_manager=risk_mgr,
            fee_calculator=fee_calc,
            mode=TradeMode.PAPER,
        )

        opp = _make_opportunity()
        result = await uc.execute(
            opportunity=opp,
            market_liquidity=Decimal("500"),
            minutes_to_close=120.0,
        )

        assert result is True
        pos_tracker.save_position.assert_called_once()
        saved_pos = pos_tracker.save_position.call_args[0][0]
        assert saved_pos.mode == TradeMode.PAPER
        assert saved_pos.status == PositionStatus.ENTERED
        assert saved_pos.market_id == "m1"

    @pytest.mark.asyncio
    async def test_rejects_below_risk_threshold(self):
        pos_tracker = AsyncMock()
        pos_tracker.get_open_positions.return_value = []

        risk_mgr = RiskManager(_make_risk_config())
        fee_calc = FeeCalculator()

        uc = ExecuteTrade(
            position_tracker=pos_tracker,
            pricing=None,
            risk_manager=risk_mgr,
            fee_calculator=fee_calc,
            mode=TradeMode.PAPER,
        )

        opp = _make_opportunity()
        result = await uc.execute(
            opportunity=opp,
            market_liquidity=Decimal("10"),  # Below minimum 100
            minutes_to_close=120.0,
        )

        assert result is False
        pos_tracker.save_position.assert_not_called()

    @pytest.mark.asyncio
    async def test_revalidates_price_when_pricing_available(self):
        pos_tracker = AsyncMock()
        pos_tracker.get_open_positions.return_value = []

        pricing = AsyncMock()
        pricing.get_best_ask.return_value = Price(Decimal("0.97"))

        risk_mgr = RiskManager(_make_risk_config())
        fee_calc = FeeCalculator()

        uc = ExecuteTrade(
            position_tracker=pos_tracker,
            pricing=pricing,
            risk_manager=risk_mgr,
            fee_calculator=fee_calc,
            mode=TradeMode.PAPER,
        )

        opp = _make_opportunity(entry_price=Decimal("0.96"))
        result = await uc.execute(
            opportunity=opp,
            market_liquidity=Decimal("500"),
            minutes_to_close=120.0,
        )

        assert result is True
        saved_pos = pos_tracker.save_position.call_args[0][0]
        assert saved_pos.entry_price == Decimal("0.97")

    @pytest.mark.asyncio
    async def test_continues_on_price_revalidation_failure(self):
        pos_tracker = AsyncMock()
        pos_tracker.get_open_positions.return_value = []

        pricing = AsyncMock()
        pricing.get_best_ask.side_effect = Exception("network error")

        risk_mgr = RiskManager(_make_risk_config())
        fee_calc = FeeCalculator()

        uc = ExecuteTrade(
            position_tracker=pos_tracker,
            pricing=pricing,
            risk_manager=risk_mgr,
            fee_calculator=fee_calc,
            mode=TradeMode.PAPER,
        )

        opp = _make_opportunity(entry_price=Decimal("0.96"))
        result = await uc.execute(
            opportunity=opp,
            market_liquidity=Decimal("500"),
            minutes_to_close=120.0,
        )

        # Should still succeed with original price
        assert result is True
        saved_pos = pos_tracker.save_position.call_args[0][0]
        assert saved_pos.entry_price == Decimal("0.96")

    @pytest.mark.asyncio
    async def test_no_side_opportunity_creates_no_side_position(self):
        pos_tracker = AsyncMock()
        pos_tracker.get_open_positions.return_value = []

        risk_mgr = RiskManager(_make_risk_config())
        fee_calc = FeeCalculator()

        uc = ExecuteTrade(
            position_tracker=pos_tracker,
            pricing=None,
            risk_manager=risk_mgr,
            fee_calculator=fee_calc,
            mode=TradeMode.PAPER,
        )

        opp = _make_opportunity(entry_price=Decimal("0.97"), side=Side.NO)
        result = await uc.execute(
            opportunity=opp,
            market_liquidity=Decimal("500"),
            minutes_to_close=120.0,
        )

        assert result is True
        saved_pos = pos_tracker.save_position.call_args[0][0]
        assert saved_pos.side == Side.NO
        assert saved_pos.token_id.value == "0xno"

    @pytest.mark.asyncio
    async def test_rejects_when_too_close_to_close(self):
        pos_tracker = AsyncMock()
        pos_tracker.get_open_positions.return_value = []

        risk_mgr = RiskManager(_make_risk_config())
        fee_calc = FeeCalculator()

        uc = ExecuteTrade(
            position_tracker=pos_tracker,
            pricing=None,
            risk_manager=risk_mgr,
            fee_calculator=fee_calc,
            mode=TradeMode.PAPER,
        )

        opp = _make_opportunity()
        result = await uc.execute(
            opportunity=opp,
            market_liquidity=Decimal("500"),
            minutes_to_close=30.0,  # Below minimum 60
        )

        assert result is False
        pos_tracker.save_position.assert_not_called()
