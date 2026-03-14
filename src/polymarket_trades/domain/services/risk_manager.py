from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from polymarket_trades.domain.entities.position import Position
from polymarket_trades.domain.strategies.opportunity import Opportunity
from polymarket_trades.domain.value_objects.money import Money

@dataclass(frozen=True)
class RiskConfig:
    total_capital: Decimal
    max_single_position_pct: Decimal
    max_total_exposure_pct: Decimal
    min_profit_threshold: Money
    min_minutes_to_close: int
    min_market_liquidity: Decimal

@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    reason: str
    max_quantity: Decimal = Decimal("0")

class RiskManager:
    def __init__(self, config: RiskConfig) -> None:
        self._config = config

    def evaluate(self, opportunity: Opportunity, current_positions: list[Position],
                 market_liquidity: Decimal, minutes_to_close: float) -> RiskDecision:
        if opportunity.expected_profit < self._config.min_profit_threshold:
            return RiskDecision(approved=False, reason="Expected profit below minimum threshold")
        if market_liquidity < self._config.min_market_liquidity:
            return RiskDecision(approved=False, reason="Insufficient market liquidity")
        if minutes_to_close < self._config.min_minutes_to_close:
            return RiskDecision(approved=False, reason="Too close to market close")

        total_exposure = sum(p.notional_value for p in current_positions if p.is_open)
        max_total = self._config.total_capital * self._config.max_total_exposure_pct
        remaining_capacity = max_total - total_exposure
        if remaining_capacity <= 0:
            return RiskDecision(approved=False, reason="Max total exposure exceeded")

        max_single = self._config.total_capital * self._config.max_single_position_pct
        max_notional = min(max_single, remaining_capacity)
        max_quantity = max_notional / opportunity.entry_price if opportunity.entry_price > 0 else Decimal("0")

        return RiskDecision(approved=True, reason="Approved", max_quantity=max_quantity)
