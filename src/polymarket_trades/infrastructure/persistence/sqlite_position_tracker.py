from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import aiosqlite

from polymarket_trades.domain.entities.position import Position
from polymarket_trades.domain.ports.position_tracker import PositionTrackerPort
from polymarket_trades.domain.value_objects.outcome import Side
from polymarket_trades.domain.value_objects.resolution_outcome import ResolutionOutcome
from polymarket_trades.domain.value_objects.token_id import TokenId
from polymarket_trades.domain.value_objects.trade_mode import PositionStatus, TradeMode

_OPEN_STATUSES = ("IDENTIFIED", "ENTERED", "MONITORING")

_ALL_COLUMNS = (
    "id, opportunity_type, market_id, token_id, side, event_title, event_slug, "
    "entry_price, quantity, detected_at, entry_time, current_price, "
    "resolution_outcome, exit_price, pnl, fees_estimated, mode, status, "
    "created_at, updated_at, market_end_date"
)


def _row_to_position(row: tuple) -> Position:
    return Position(
        id=uuid.UUID(row[0]),
        opportunity_type=row[1],
        market_id=row[2],
        token_id=TokenId(row[3]),
        side=Side(row[4]),
        event_title=row[5],
        event_slug=row[6],
        entry_price=Decimal(row[7]),
        quantity=Decimal(row[8]),
        detected_at=datetime.fromisoformat(row[9]),
        entry_time=datetime.fromisoformat(row[10]),
        current_price=Decimal(row[11]),
        resolution_outcome=ResolutionOutcome(row[12]) if row[12] else None,
        exit_price=Decimal(row[13]) if row[13] else None,
        pnl=Decimal(row[14]) if row[14] else None,
        fees_estimated=Decimal(row[15]),
        mode=TradeMode(row[16]),
        status=PositionStatus(row[17]),
        created_at=datetime.fromisoformat(row[18]),
        updated_at=datetime.fromisoformat(row[19]),
        market_end_date=datetime.fromisoformat(row[20]) if row[20] else None,
    )


class SqlitePositionTracker(PositionTrackerPort):
    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    async def save_position(self, position: Position) -> None:
        await self._db.execute(
            f"INSERT INTO positions ({_ALL_COLUMNS}) "
            f"VALUES ({','.join('?' for _ in range(21))})",
            (
                str(position.id),
                position.opportunity_type,
                position.market_id,
                position.token_id.value,
                position.side.value,
                position.event_title,
                position.event_slug,
                str(position.entry_price),
                str(position.quantity),
                position.detected_at.isoformat(),
                position.entry_time.isoformat(),
                str(position.current_price),
                position.resolution_outcome.value if position.resolution_outcome else None,
                str(position.exit_price) if position.exit_price is not None else None,
                str(position.pnl) if position.pnl is not None else None,
                str(position.fees_estimated),
                position.mode.value,
                position.status.value,
                position.created_at.isoformat(),
                position.updated_at.isoformat(),
                position.market_end_date.isoformat() if position.market_end_date else None,
            ),
        )
        await self._db.commit()

    async def get_open_positions(self) -> list[Position]:
        placeholders = ",".join("?" for _ in _OPEN_STATUSES)
        async with self._db.execute(
            f"SELECT {_ALL_COLUMNS} FROM positions WHERE status IN ({placeholders})",
            _OPEN_STATUSES,
        ) as cursor:
            return [_row_to_position(row) for row in await cursor.fetchall()]

    async def get_position_by_market(self, market_id: str) -> Position | None:
        async with self._db.execute(
            f"SELECT {_ALL_COLUMNS} FROM positions WHERE market_id = ? LIMIT 1",
            (market_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return _row_to_position(row) if row else None

    async def update_position(self, position: Position) -> None:
        position.updated_at = datetime.now(timezone.utc)
        await self._db.execute(
            "UPDATE positions SET current_price=?, resolution_outcome=?, exit_price=?, "
            "pnl=?, status=?, updated_at=? WHERE id=?",
            (
                str(position.current_price),
                position.resolution_outcome.value if position.resolution_outcome else None,
                str(position.exit_price) if position.exit_price is not None else None,
                str(position.pnl) if position.pnl is not None else None,
                position.status.value,
                position.updated_at.isoformat(),
                str(position.id),
            ),
        )
        await self._db.commit()

    async def update_event_slug(self, position_id: str, event_slug: str) -> None:
        await self._db.execute(
            "UPDATE positions SET event_slug = ? WHERE id = ?",
            (event_slug, position_id),
        )
        await self._db.commit()

    async def get_all_positions(self, mode: TradeMode | None = None) -> list[Position]:
        if mode:
            async with self._db.execute(
                f"SELECT {_ALL_COLUMNS} FROM positions WHERE mode = ?",
                (mode.value,),
            ) as cursor:
                return [_row_to_position(row) for row in await cursor.fetchall()]
        async with self._db.execute(
            f"SELECT {_ALL_COLUMNS} FROM positions"
        ) as cursor:
            return [_row_to_position(row) for row in await cursor.fetchall()]
