"""Same SQL on SQLite (local dev, tests) and Postgres (production on Supabase).

DATABASE_URL=postgresql://... switches to Postgres (psycopg). Queries are written with "?"
placeholders and portable SQL; the few engine-specific needs go through `begin_write()` and `lock()`.
"""
from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "")
PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))
# Several apps can share one Supabase project: each keeps its tables in its own schema.
SCHEMA = re.sub(r"[^a-z0-9_]", "", os.getenv("DB_SCHEMA", "public").lower()) or "public"


class Conn:
    def __init__(self, raw):
        self.raw = raw

    def execute(self, sql: str, params: tuple | list = ()):
        if PG:
            cur = self.raw.cursor()
            cur.execute(sql.replace("?", "%s"), params)
            return cur
        return self.raw.execute(sql, params)

    def executescript(self, script: str) -> None:
        if PG:
            for stmt in (s.strip() for s in script.split(";")):
                if stmt:
                    # REAL is 4 bytes in Postgres: far too imprecise for timestamps
                    self.raw.execute(re.sub(r"\bREAL\b", "DOUBLE PRECISION", stmt))
        else:
            self.raw.executescript(script)

    def begin_write(self) -> None:
        """Start a transaction that serialises writers (credits must not be spent twice)."""
        if not PG:
            self.raw.execute("BEGIN IMMEDIATE")

    def lock(self, sql: str, params: tuple | list = ()):
        """SELECT that locks the rows it reads until commit (Postgres); SQLite is already locked."""
        return self.execute(sql + (" FOR UPDATE" if PG else ""), params)

    def columns(self, table: str) -> set[str]:
        if PG:
            rows = self.execute("SELECT column_name FROM information_schema.columns WHERE table_name = ? AND table_schema = ?", (table, SCHEMA)).fetchall()
            return {r["column_name"] for r in rows}
        return {r[1] for r in self.raw.execute(f"PRAGMA table_info({table})")}


_pool = None
_schema_ready = False


def _pg_pool():
    """Connections to Supabase kept open between requests: opening one costs ~0.6 s from the server (TLS, far away),
    as much as the work of a whole request. prepare_threshold=None: required behind Supabase's connection pooler."""
    global _pool
    if _pool is None:
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        _pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=8, max_idle=120, max_lifetime=900, timeout=20, open=True,
                               kwargs={"row_factory": dict_row, "prepare_threshold": None, "connect_timeout": 15})
    return _pool


@contextmanager
def connect(sqlite_path: Path):
    if PG:
        import psycopg

        global _schema_ready
        pool = _pg_pool()
        # One retry: a connection the pooler closed while it slept (or a network blip) must not become an error for the user.
        for attempt in (1, 2):
            conn = pool.getconn()
            try:
                if SCHEMA != "public":
                    if not _schema_ready:
                        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
                        _schema_ready = True
                    conn.execute(f"SET LOCAL search_path TO {SCHEMA}")  # LOCAL: safe behind a transaction pooler
                break
            except psycopg.OperationalError:
                pool.putconn(conn)  # a broken connection is thrown away by the pool
                if attempt == 2:
                    raise
        try:
            yield Conn(conn)
            conn.commit()
        except Exception:
            if not conn.closed:
                conn.rollback()
            raise
        finally:
            pool.putconn(conn)
        return
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(sqlite_path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield Conn(conn)
        conn.commit()
    finally:
        conn.close()
