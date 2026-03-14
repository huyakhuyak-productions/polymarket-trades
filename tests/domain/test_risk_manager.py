import uuid
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from polymarket_trades.domain.entities.position import Position
from polymarket_trades.domain.services.risk_manager import RiskManager, RiskConfig, RiskDecision
from polymarket_trades.domain.strategies.opportunity import Opportunity
from polymarket_trades.domain.value_objects.money import Money
from polymarket_trades.domain.value_objects.outcome import Side
from polymarket_trades.domain.value_objects.token_id import TokenId
from polymarket_trades.domain.value_objects.trade_mode import TradeMode, PositionStatus

def _make_opportunity(**overrides) -> Opportunity:
    defaults = {"strategy_type": "near_certain", "market_id": "m1", "token_id": "0xyes",
                "event_title": "Test", "expected_profit": Money(Decimal("2.00")), "entry_price": Decimal("0.96")}
    defaults.update(overrides)
    return Opportunity(**defaults)

def _make_position(**overrides) -> Position:
    now = datetime(2026, 3, 13, tzinfo=timezone.utc)
    defaults = {"id": uuid.uuid4(), "opportunity_type": "near_certain", "market_id": "m-existing",
                "token_id": TokenId("0xold"), "side": Side.YES, "event_title": "Existing",
                "entry_price": Decimal("0.96"), "quantity": Decimal("100"), "detected_at": now,
                "entry_time": now, "current_price": Decimal("0.96"), "resolution_outcome": None,
                "exit_price": None, "pnl": None, "fees_estimated": Decimal("0"),
                "mode": TradeMode.PAPER, "status": PositionStatus.MONITORING}
    defaults.update(overrides)
    return Position(**defaults)

class TestRiskManager:
    def setup_method(self):
        self.config = RiskConfig(total_capital=Decimal("1000"), max_single_position_pct=Decimal("0.20"),
            max_total_exposure_pct=Decimal("0.80"), min_profit_threshold=Money(Decimal("0.50")),
            min_minutes_to_close=60, min_market_liquidity=Decimal("100"))
        self.rm = RiskManager(self.config)

    def test_approve_valid_opportunity(self):
        decision = self.rm.evaluate(_make_opportunity(expected_profit=Money(Decimal("2.00"))),
            current_positions=[], market_liquidity=Decimal("5000"), minutes_to_close=120)
        assert decision.approved is True

    def test_reject_below_profit_threshold(self):
        decision = self.rm.evaluate(_make_opportunity(expected_profit=Money(Decimal("0.10"))),
            current_positions=[], market_liquidity=Decimal("5000"), minutes_to_close=120)
        assert decision.approved is False
        assert "profit" in decision.reason.lower()

    def test_reject_insufficient_liquidity(self):
        decision = self.rm.evaluate(_make_opportunity(), current_positions=[],
            market_liquidity=Decimal("50"), minutes_to_close=120)
        assert decision.approved is False
        assert "liquidity" in decision.reason.lower()

    def test_reject_too_close_to_resolution(self):
        decision = self.rm.evaluate(_make_opportunity(), current_positions=[],
            market_liquidity=Decimal("5000"), minutes_to_close=30)
        assert decision.approved is False
        assert "close" in decision.reason.lower()

    def test_reject_exceeds_max_total_exposure(self):
        existing = _make_position(entry_price=Decimal("0.80"), quantity=Decimal("1000"))
        decision = self.rm.evaluate(_make_opportunity(), current_positions=[existing],
            market_liquidity=Decimal("5000"), minutes_to_close=120)
        assert decision.approved is False
        assert "exposure" in decision.reason.lower()

    def test_position_size_capped_at_max_single(self):
        decision = self.rm.evaluate(_make_opportunity(entry_price=Decimal("0.96")),
            current_positions=[], market_liquidity=Decimal("5000"), minutes_to_close=120)
        assert decision.approved is True
        expected_max = Decimal("1000") * Decimal("0.20") / Decimal("0.96")
        assert decision.max_quantity == expected_max
