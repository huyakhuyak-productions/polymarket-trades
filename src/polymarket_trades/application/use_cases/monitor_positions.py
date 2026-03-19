from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from polymarket_trades.domain.ports.position_tracker import PositionTrackerPort
from polymarket_trades.domain.value_objects.trade_mode import TradeMode


@dataclass
class StrategyReport:
    strategy: str
    trades: int
    wins: int
    total_pnl: Decimal
    total_cost: Decimal
    avg_return_pct: Decimal

    @property
    def total_return_pct(self) -> Decimal:
        if self.total_cost == 0:
            return Decimal("0")
        return (self.total_pnl / self.total_cost) * 100

    @property
    def win_pct(self) -> Decimal:
        return (
            Decimal(self.wins) / Decimal(self.trades) * 100
            if self.trades
            else Decimal("0")
        )


class MonitorPositions:
    def __init__(self, position_tracker: PositionTrackerPort) -> None:
        self._pos_tracker = position_tracker

    async def execute(
        self, mode: TradeMode | None = None
    ) -> list[StrategyReport]:
        positions = await self._pos_tracker.get_all_positions(mode=mode)
        resolved = [p for p in positions if p.pnl is not None]

        by_strategy: dict[str, list] = {}
        for p in resolved:
            by_strategy.setdefault(p.opportunity_type, []).append(p)

        reports = []
        for strategy, plist in sorted(by_strategy.items()):
            wins = sum(1 for p in plist if p.pnl and p.pnl > 0)
            total_pnl = sum((p.pnl for p in plist if p.pnl), Decimal("0"))
            total_cost = sum(p.notional_value for p in plist)
            returns = [p.return_pct for p in plist if p.return_pct is not None]
            avg_return_pct = (
                sum(returns, Decimal("0")) / len(returns) if returns else Decimal("0")
            )
            reports.append(
                StrategyReport(
                    strategy=strategy,
                    trades=len(plist),
                    wins=wins,
                    total_pnl=total_pnl,
                    total_cost=total_cost,
                    avg_return_pct=avg_return_pct,
                )
            )

        return reports
