from __future__ import annotations

from pathlib import Path

import aiosqlite

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


async def get_current_version(db: aiosqlite.Connection) -> int:
    try:
        async with db.execute("SELECT MAX(version) FROM schema_version") as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else 0
    except Exception:
        return 0


async def run_migrations(db: aiosqlite.Connection) -> int:
    current = await get_current_version(db)
    migration_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))
    applied = 0
    for f in migration_files:
        version = int(f.stem.split("_")[0])
        if version > current:
            sql = f.read_text()
            await db.executescript(sql)
            applied += 1
    await db.commit()
    return current + applied
