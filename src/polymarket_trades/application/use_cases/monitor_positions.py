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
    avg_return_pct: Decimal

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
            avg_return = total_pnl / len(plist) if plist else Decimal("0")
            reports.append(
                StrategyReport(
                    strategy=strategy,
                    trades=len(plist),
                    wins=wins,
                    total_pnl=total_pnl,
                    avg_return_pct=avg_return,
                )
            )

        return reports
