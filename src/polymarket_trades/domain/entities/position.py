from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from polymarket_trades.domain.value_objects.outcome import Side
from polymarket_trades.domain.value_objects.resolution_outcome import ResolutionOutcome
from polymarket_trades.domain.value_objects.token_id import TokenId
from polymarket_trades.domain.value_objects.trade_mode import PositionStatus, TradeMode

_OPEN_STATUSES = {PositionStatus.IDENTIFIED, PositionStatus.ENTERED, PositionStatus.MONITORING}


@dataclass
class Position:
    id: uuid.UUID
    opportunity_type: str
    market_id: str
    token_id: TokenId
    side: Side
    event_title: str
    entry_price: Decimal
    quantity: Decimal
    detected_at: datetime
    entry_time: datetime
    current_price: Decimal
    resolution_outcome: ResolutionOutcome | None
    exit_price: Decimal | None
    pnl: Decimal | None
    fees_estimated: Decimal
    mode: TradeMode
    status: PositionStatus
    event_slug: str = ""
    market_end_date: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_open(self) -> bool:
        return self.status in _OPEN_STATUSES

    @property
    def notional_value(self) -> Decimal:
        return self.entry_price * self.quantity

    @property
    def return_pct(self) -> Decimal | None:
        if self.pnl is None or self.notional_value == 0:
            return None
        return (self.pnl / self.notional_value) * 100

    def _is_winning_outcome(self, outcome: ResolutionOutcome) -> bool:
        return (
            (self.side == Side.YES and outcome == ResolutionOutcome.YES)
            or (self.side == Side.NO and outcome == ResolutionOutcome.NO)
        )

    def resolve(self, outcome: ResolutionOutcome) -> None:
        self.resolution_outcome = outcome
        if outcome == ResolutionOutcome.INVALID:
            self.exit_price = self.entry_price
            self.pnl = Decimal("0")
        elif self._is_winning_outcome(outcome):
            self.exit_price = Decimal("1.0")
            self.pnl = (Decimal("1.0") - self.entry_price) * self.quantity - self.fees_estimated
        else:
            self.exit_price = Decimal("0")
            self.pnl = (Decimal("0") - self.entry_price) * self.quantity - self.fees_estimated
        self.status = PositionStatus.PNL_CALCULATED
        self.updated_at = datetime.now(timezone.utc)
