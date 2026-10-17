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
CREATE TABLE IF NOT EXISTS accounts (
    sub TEXT PRIMARY KEY,              -- Google's stable account id
    email TEXT NOT NULL,
    pass_until REAL NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);
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
    """Move a PENDING order to its final status. Idempotent: returns False if already settled.

    A paid pass order extends its account's pass in the same transaction (credited exactly once).
    """
    now = time.time()
    with connect() as c:
        cur = c.execute(
            "UPDATE orders SET status = ?, paid_at = CASE WHEN ? = 'PAID' THEN ? ELSE paid_at END "
            "WHERE id = ? AND status = 'PENDING'",
            (status, status, now, order_id),
        )
        if cur.rowcount != 1:
            return False
        if status == "PAID":
            row = c.execute("SELECT payload FROM orders WHERE id = ?", (order_id,)).fetchone()
            sub = json.loads(row["payload"]).get("pass_for")
            if sub:
                c.execute(
                    "UPDATE accounts SET pass_until = (CASE WHEN pass_until > ? THEN pass_until ELSE ? END) + ? WHERE sub = ?",
                    (now, now, PASS_DAYS * 86400, sub),
                )
        return True


PASS_DAYS = 30


def grant(order_id: str, note: str = "") -> None:
    """Unlocks an order without a payment (the team's own documents, or a customer's active pass)."""
    with connect() as c:
        c.execute(
            "UPDATE orders SET status = 'PAID', paid_at = ?, trans_id = COALESCE(NULLIF(?, ''), trans_id) WHERE id = ? AND status != 'PAID'",
            (time.time(), note[:60], order_id),
        )


def save_account(sub: str, email: str) -> dict:
    with connect() as c:
        if c.execute("SELECT 1 FROM accounts WHERE sub = ?", (sub,)).fetchone():
            c.execute("UPDATE accounts SET email = ? WHERE sub = ?", (email, sub))
        else:
            c.execute("INSERT INTO accounts (sub, email, created_at) VALUES (?,?,?)", (sub, email, time.time()))
    return get_account(sub)


def get_account(sub: str) -> dict | None:
    with connect() as c:
        row = c.execute("SELECT * FROM accounts WHERE sub = ?", (sub,)).fetchone()
    return dict(row) if row else None


def set_product(order_id: str, product: str, amount: int) -> None:
    """Price follows the document size, but never changes once paid or pending."""
    with connect() as c:
        c.execute(
            "UPDATE orders SET product = ?, amount = ? WHERE id = ? AND status NOT IN ('PAID', 'PENDING')",
            (product, amount, order_id),
        )
