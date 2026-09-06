"""Database access.

Deliberately thin: a single SQLAlchemy engine plus helpers that take raw SQL.
`schema.sql` is the single source of truth for the schema (it is the artifact
referenced by the report's architecture figures), so there is no ORM model
layer that could drift away from it.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from api.settings import get_settings

SCHEMA_SQL = Path(__file__).resolve().parent / "schema.sql"

_engine: Engine | None = None


def get_engine() -> Engine:
    """Process-wide engine with a small pool and liveness checking."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_settings().database_url,
            pool_size=5,
            max_overflow=5,
            pool_pre_ping=True,
            future=True,
        )
    return _engine


@contextmanager
def connection() -> Iterator[Connection]:
    """A transactional connection: commits on success, rolls back on error."""
    with get_engine().begin() as conn:
        yield conn


def init_schema() -> None:
    """Apply schema.sql. Every statement is IF NOT EXISTS, so this is safe on
    every boot and doubles as the migration story for a project this size."""
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    with connection() as conn:
        conn.execute(text(sql))


def fetch_all(sql: str, **params: Any) -> list[dict]:
    with connection() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


def fetch_one(sql: str, **params: Any) -> dict | None:
    with connection() as conn:
        row = conn.execute(text(sql), params).mappings().first()
    return dict(row) if row else None


def execute(sql: str, **params: Any) -> None:
    with connection() as conn:
        conn.execute(text(sql), params)


def execute_many(sql: str, rows: list[dict]) -> None:
    """Bulk insert/update in one round-trip and one transaction.

    Passing a list of dicts makes SQLAlchemy use executemany, which matters for
    event ingestion where a single batch can carry dozens of rows.
    """
    if not rows:
        return
    with connection() as conn:
        conn.execute(text(sql), rows)


def ping() -> bool:
    try:
        with connection() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
