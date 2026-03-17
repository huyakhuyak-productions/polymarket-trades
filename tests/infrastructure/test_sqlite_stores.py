import uuid
from datetime import datetime, timezone
from decimal import Decimal

import aiosqlite
import pytest

from polymarket_trades.domain.entities.position import Position
from polymarket_trades.domain.strategies.opportunity import Opportunity
from polymarket_trades.domain.value_objects.money import Money
from polymarket_trades.domain.value_objects.outcome import Side
from polymarket_trades.domain.value_objects.token_id import TokenId
from polymarket_trades.domain.value_objects.trade_mode import PositionStatus, TradeMode
from polymarket_trades.infrastructure.persistence.migrator import run_migrations
from polymarket_trades.infrastructure.persistence.sqlite_opportunity_store import (
    SqliteOpportunityStore,
)
from polymarket_trades.infrastructure.persistence.sqlite_position_tracker import (
    SqlitePositionTracker,
)


@pytest.fixture
async def db():
    conn = await aiosqlite.connect(":memory:")
    await run_migrations(conn)
    yield conn
    await conn.close()


def _make_opportunity(**overrides):
    defaults = {
        "strategy_type": "near_certain",
        "market_id": "m1",
        "token_id": "0xyes",
        "event_title": "Test",
        "expected_profit": Money(Decimal("2.00")),
        "entry_price": Decimal("0.96"),
    }
    defaults.update(overrides)
    return Opportunity(**defaults)


def _make_position(**overrides):
    now = datetime(2026, 3, 13, 12, 0, tzinfo=timezone.utc)
    defaults = {
        "id": uuid.uuid4(),
        "opportunity_type": "near_certain",
        "market_id": "m1",
        "token_id": TokenId("0xyes"),
        "side": Side.YES,
        "event_title": "Test",
        "event_slug": "test-event",
        "entry_price": Decimal("0.96"),
        "quantity": Decimal("50"),
        "detected_at": now,
        "entry_time": now,
        "current_price": Decimal("0.96"),
        "resolution_outcome": None,
        "exit_price": None,
        "pnl": None,
        "fees_estimated": Decimal("0.10"),
        "mode": TradeMode.PAPER,
        "status": PositionStatus.MONITORING,
    }
    defaults.update(overrides)
    return Position(**defaults)


class TestMigrator:
    @pytest.mark.asyncio
    async def test_migration_creates_tables(self, db):
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ) as cur:
            tables = {row[0] for row in await cur.fetchall()}
        assert "positions" in tables
        assert "opportunities" in tables

    @pytest.mark.asyncio
    async def test_migration_is_idempotent(self, db):
        """Running migrations again should not fail."""
        version = await run_migrations(db)
        assert version >= 1


class TestSqliteOpportunityStore:
    @pytest.mark.asyncio
    async def test_save_and_find(self, db):
        store = SqliteOpportunityStore(db)
        await store.save(_make_opportunity())
        found = await store.find_existing("near_certain", "m1", "0xyes")
        assert found is not None
        assert found.strategy_type == "near_certain"

    @pytest.mark.asyncio
    async def test_find_returns_none(self, db):
        store = SqliteOpportunityStore(db)
        assert await store.find_existing("x", "y", "z") is None

    @pytest.mark.asyncio
    async def test_save_preserves_money_precision(self, db):
        store = SqliteOpportunityStore(db)
        opp = _make_opportunity(expected_profit=Money(Decimal("0.123456")))
        await store.save(opp)
        found = await store.find_existing("near_certain", "m1", "0xyes")
        assert found is not None
        assert found.expected_profit.value == Decimal("0.123456")

    @pytest.mark.asyncio
    async def test_find_returns_latest(self, db):
        store = SqliteOpportunityStore(db)
        await store.save(_make_opportunity(entry_price=Decimal("0.90")))
        await store.save(_make_opportunity(entry_price=Decimal("0.96")))
        found = await store.find_existing("near_certain", "m1", "0xyes")
        assert found is not None
        assert found.entry_price == Decimal("0.96")

    @pytest.mark.asyncio
    async def test_event_slug_roundtrip(self, db):
        store = SqliteOpportunityStore(db)
        opp = _make_opportunity(event_slug="test-slug")
        await store.save(opp)
        found = await store.find_existing("near_certain", "m1", "0xyes")
        assert found is not None
        assert found.event_slug == "test-slug"


class TestSqlitePositionTracker:
    @pytest.mark.asyncio
    async def test_save_and_get_open(self, db):
        tracker = SqlitePositionTracker(db)
        await tracker.save_position(_make_position())
        open_pos = await tracker.get_open_positions()
        assert len(open_pos) == 1
        assert open_pos[0].market_id == "m1"

    @pytest.mark.asyncio
    async def test_get_by_market(self, db):
        tracker = SqlitePositionTracker(db)
        await tracker.save_position(_make_position(market_id="m1"))
        await tracker.save_position(
            _make_position(id=uuid.uuid4(), market_id="m2")
        )
        found = await tracker.get_position_by_market("m1")
        assert found is not None and found.market_id == "m1"

    @pytest.mark.asyncio
    async def test_get_by_market_returns_none(self, db):
        tracker = SqlitePositionTracker(db)
        assert await tracker.get_position_by_market("nonexistent") is None

    @pytest.mark.asyncio
    async def test_update_position(self, db):
        tracker = SqlitePositionTracker(db)
        pos = _make_position()
        await tracker.save_position(pos)
        pos.status = PositionStatus.RESOLVED
        pos.current_price = Decimal("1.0")
        await tracker.update_position(pos)
        updated = await tracker.get_position_by_market("m1")
        assert updated.status == PositionStatus.RESOLVED

    @pytest.mark.asyncio
    async def test_filter_by_mode(self, db):
        tracker = SqlitePositionTracker(db)
        await tracker.save_position(_make_position(mode=TradeMode.PAPER))
        await tracker.save_position(
            _make_position(
                id=uuid.uuid4(), mode=TradeMode.LIVE, market_id="m2"
            )
        )
        assert len(await tracker.get_all_positions(mode=TradeMode.PAPER)) == 1
        assert len(await tracker.get_all_positions()) == 2

    @pytest.mark.asyncio
    async def test_closed_positions_not_in_open(self, db):
        tracker = SqlitePositionTracker(db)
        pos = _make_position(status=PositionStatus.PNL_CALCULATED)
        await tracker.save_position(pos)
        open_pos = await tracker.get_open_positions()
        assert len(open_pos) == 0

    @pytest.mark.asyncio
    async def test_roundtrip_preserves_all_fields(self, db):
        tracker = SqlitePositionTracker(db)
        pos = _make_position()
        await tracker.save_position(pos)
        loaded = await tracker.get_position_by_market("m1")
        assert loaded.id == pos.id
        assert loaded.token_id.value == pos.token_id.value
        assert loaded.side == pos.side
        assert loaded.entry_price == pos.entry_price
        assert loaded.quantity == pos.quantity
        assert loaded.fees_estimated == pos.fees_estimated
        assert loaded.mode == pos.mode
        assert loaded.event_slug == pos.event_slug

    @pytest.mark.asyncio
    async def test_event_slug_roundtrip(self, db):
        tracker = SqlitePositionTracker(db)
        pos = _make_position(event_slug="will-trump-win-2028")
        await tracker.save_position(pos)
        loaded = await tracker.get_position_by_market("m1")
        assert loaded.event_slug == "will-trump-win-2028"

    @pytest.mark.asyncio
    async def test_event_slug_defaults_to_empty(self, db):
        tracker = SqlitePositionTracker(db)
        pos = _make_position()
        await tracker.save_position(pos)
        loaded = await tracker.get_position_by_market("m1")
        assert loaded.event_slug == "test-event"
