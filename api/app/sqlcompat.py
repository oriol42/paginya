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


@contextmanager
def connect(sqlite_path: Path):
    if PG:
        import psycopg
        from psycopg.rows import dict_row

        # prepare_threshold=None: required behind Supabase's connection pooler
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row, prepare_threshold=None, connect_timeout=10)
        if SCHEMA != "public":
            conn.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
            conn.execute(f"SET LOCAL search_path TO {SCHEMA}")  # LOCAL: safe behind a transaction pooler
        try:
            yield Conn(conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        return
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(sqlite_path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield Conn(conn)
        conn.commit()
    finally:
        conn.close()
