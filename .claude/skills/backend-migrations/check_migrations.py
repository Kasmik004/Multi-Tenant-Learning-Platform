"""Round-trip every migration on a throwaway DB and report model/schema drift.

Run from backend/:  uv run python ../.claude/skills/backend-migrations/check_migrations.py [--keep]
--keep leaves `migration_check` at head for manual inspection (drop it yourself afterwards).
"""

import asyncio
import os
import subprocess
import sys

DB = "migration_check"
os.environ["POSTGRES_DB"] = DB  # before importing settings
sys.path.insert(0, os.getcwd())

import asyncpg  # noqa: E402
from alembic.autogenerate import compare_metadata  # noqa: E402
from alembic.migration import MigrationContext  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.models import Base  # noqa: E402


async def admin(sql: str) -> None:
    conn = await asyncpg.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database="postgres",
    )
    try:
        await conn.execute(sql)
    finally:
        await conn.close()


def alembic(*args: str) -> None:
    print(f"$ alembic {' '.join(args)}")
    result = subprocess.run(["uv", "run", "alembic", *args], capture_output=True, text=True)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(f"alembic {' '.join(args)} failed")


async def drift() -> list[str]:
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        diffs = await conn.run_sync(
            lambda c: compare_metadata(
                MigrationContext.configure(c, opts={"compare_type": True}), Base.metadata
            )
        )
    await engine.dispose()
    out = []
    for d in diffs:
        d = d[0] if isinstance(d, list) else d
        obj = d[-1]
        out.append(f"{d[0]}: {getattr(obj, 'name', obj)}")
    return out


async def main() -> None:
    keep = "--keep" in sys.argv
    await admin(f'DROP DATABASE IF EXISTS "{DB}"')
    await admin(f'CREATE DATABASE "{DB}"')
    try:
        alembic("upgrade", "head")
        alembic("downgrade", "base")
        alembic("upgrade", "head")
        print("Round trip OK. Drift between models and migrated schema:")
        for line in await drift() or ["(none)"]:
            print("  ", line)
    finally:
        if not keep:
            await admin(f'DROP DATABASE IF EXISTS "{DB}"')


asyncio.run(main())
