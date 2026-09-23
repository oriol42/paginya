"""Orders store: SQLite locally, Postgres (Supabase) in production — see sqlcompat."""
import json
import time
import uuid
from contextlib import contextmanager

from . import sqlcompat
from .config import DATA_DIR, DB_PATH  # noqa: F401  (DATA_DIR: patched by tests)

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    product TEXT NOT NULL,
    amount INTEGER NOT NULL,
    status TEXT NOT NULL,              -- DRAFT, PENDING, PAID, FAILED, EXPIRED
    payload TEXT NOT NULL,             -- JSON: the document (e.g. cover svg + form data)
    phone TEXT,
    trans_id TEXT,
    created_at REAL NOT NULL,
    paid_at REAL
);
CREATE INDEX IF NOT EXISTS orders_trans ON orders(trans_id);
"""


@contextmanager
def connect():
    with sqlcompat.connect(DB_PATH) as c:
        yield c


def init() -> None:
    with connect() as c:
        c.executescript(SCHEMA)


def create_order(product: str, amount: int, payload: dict) -> str:
    order_id = uuid.uuid4().hex  # also the secret link to the document
    with connect() as c:
        c.execute(
            "INSERT INTO orders (id, product, amount, status, payload, created_at) VALUES (?,?,?,?,?,?)",
            (order_id, product, amount, "DRAFT", json.dumps(payload), time.time()),
        )
    return order_id


def get_order(order_id: str) -> dict | None:
    with connect() as c:
        row = c.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        return None
    order = dict(row)
    order["payload"] = json.loads(order["payload"])
    return order


def update_payload(order_id: str, payload: dict) -> None:
    with connect() as c:
        c.execute("UPDATE orders SET payload = ? WHERE id = ?", (json.dumps(payload), order_id))


def mark_pending(order_id: str, phone: str, trans_id: str) -> None:
    with connect() as c:
        c.execute(
            "UPDATE orders SET status = 'PENDING', phone = ?, trans_id = ? WHERE id = ?",
            (phone, trans_id, order_id),
        )


def settle(order_id: str, status: str) -> bool:
    """Move a PENDING order to its final status. Idempotent: returns False if already settled."""
    with connect() as c:
        cur = c.execute(
            "UPDATE orders SET status = ?, paid_at = CASE WHEN ? = 'PAID' THEN ? ELSE paid_at END "
            "WHERE id = ? AND status = 'PENDING'",
            (status, status, time.time(), order_id),
        )
        return cur.rowcount == 1


def set_product(order_id: str, product: str, amount: int) -> None:
    """Price follows the document size, but never changes once paid or pending."""
    with connect() as c:
        c.execute(
            "UPDATE orders SET product = ?, amount = ? WHERE id = ? AND status NOT IN ('PAID', 'PENDING')",
            (product, amount, order_id),
        )
