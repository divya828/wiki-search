from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import asyncpg
from pgvector.asyncpg import register_vector

from app.config import get_settings

_pool: asyncpg.Pool | None = None
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def _connect_kwargs() -> dict[str, Any]:
    """
    Parse DATABASE_URL with urllib and return asyncpg connect kwargs.

    asyncpg's built-in DSN parser truncates usernames at the first '.', which
    breaks Supabase's pooler usernames (e.g. "postgres.<project-ref>"). Passing
    kwargs explicitly bypasses that.
    """
    p = urlparse(get_settings().database_url)
    return {
        "user": unquote(p.username) if p.username else None,
        "password": unquote(p.password) if p.password else None,
        "host": p.hostname,
        "port": p.port or 5432,
        "database": p.path.lstrip("/") or None,
    }


async def _run_migrations(conn: asyncpg.Connection) -> None:
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        await conn.execute(path.read_text())


async def init_pool() -> asyncpg.Pool:
    """Bootstrap the schema, then create the connection pool."""
    global _pool
    kwargs = _connect_kwargs()
    bootstrap = await asyncpg.connect(**kwargs)
    try:
        await _run_migrations(bootstrap)
    finally:
        await bootstrap.close()
    _pool = await asyncpg.create_pool(
        min_size=1,
        max_size=5,
        init=_init_connection,
        **kwargs,
    )
    return _pool


async def _init_connection(conn: asyncpg.Connection) -> None:
    schema = await conn.fetchval(
        "SELECT typnamespace::regnamespace::text FROM pg_type WHERE typname = 'vector'"
    )
    await register_vector(conn, schema=schema or "public")


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialized; call init_pool() first")
    return _pool
