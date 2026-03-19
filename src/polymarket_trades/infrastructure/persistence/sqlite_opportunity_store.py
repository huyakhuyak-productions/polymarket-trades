from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import aiosqlite

from polymarket_trades.domain.ports.opportunity_store import OpportunityStorePort
from polymarket_trades.domain.strategies.opportunity import Opportunity
from polymarket_trades.domain.value_objects.money import Money
from polymarket_trades.domain.value_objects.outcome import Side


class SqliteOpportunityStore(OpportunityStorePort):
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def save(self, opportunity: Opportunity) -> None:
        await self._db.execute(
            "INSERT INTO opportunities "
            "(strategy_type, market_id, token_id, event_title, expected_profit, entry_price, detected_at, event_slug, side) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                opportunity.strategy_type,
                opportunity.market_id,
                opportunity.token_id,
                opportunity.event_title,
                str(opportunity.expected_profit.value),
                str(opportunity.entry_price),
                opportunity.detected_at.isoformat(),
                opportunity.event_slug,
                opportunity.side.value,
            ),
        )
        await self._db.commit()

    async def find_existing(
        self, strategy_type: str, market_id: str, token_id: str
    ) -> Opportunity | None:
        async with self._db.execute(
            "SELECT strategy_type, market_id, token_id, event_title, expected_profit, "
            "entry_price, detected_at, event_slug, side "
            "FROM opportunities "
            "WHERE strategy_type = ? AND market_id = ? AND token_id = ? "
            "ORDER BY rowid DESC LIMIT 1",
            (strategy_type, market_id, token_id),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return Opportunity(
                strategy_type=row[0],
                market_id=row[1],
                token_id=row[2],
                event_title=row[3],
                expected_profit=Money(Decimal(row[4])),
                entry_price=Decimal(row[5]),
                side=Side(row[8]),
                detected_at=datetime.fromisoformat(row[6]),
                event_slug=row[7],
            )
