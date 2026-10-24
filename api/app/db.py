"""Orders store: SQLite locally, Postgres (Supabase) in production — see sqlcompat."""
import json
import time
import uuid
from contextlib import contextmanager

from . import pricing, sqlcompat
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
    plan TEXT NOT NULL DEFAULT '',     -- essentiel or pro ('' = the first passes, sold at the Pro price)
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS events (    -- visitor funnel: one row per visitor (sid) and step
    sid TEXT NOT NULL,                 -- random id kept by the browser, nothing personal
    step TEXT NOT NULL,
    src TEXT NOT NULL,                 -- where the visitor came from: facebook, tiktok, google, direct…
    day TEXT NOT NULL,
    ts REAL NOT NULL,
    PRIMARY KEY (sid, step)
);
CREATE TABLE IF NOT EXISTS tickets (   -- support: a customer writes, both team members see and answer
    id TEXT PRIMARY KEY,               -- also the customer's secret link to the conversation
    sub TEXT,                          -- the customer's account, when signed in
    name TEXT NOT NULL,
    contact TEXT NOT NULL,             -- WhatsApp number or e-mail, to answer outside the site too
    order_id TEXT,
    status TEXT NOT NULL,              -- NEW (our turn), ANSWERED (the customer's turn), CLOSED
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS ticket_messages (
    ticket_id TEXT NOT NULL,
    author TEXT NOT NULL,              -- "client", or the team member's e-mail
    body TEXT NOT NULL,
    ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ticket_messages_ticket ON ticket_messages(ticket_id);
"""


@contextmanager
def connect():
    with sqlcompat.connect(DB_PATH) as c:
        yield c


def init() -> None:
    with connect() as c:
        c.executescript(SCHEMA)
        if "plan" not in c.columns("accounts"):  # databases made before the plans
            c.execute("ALTER TABLE accounts ADD COLUMN plan TEXT NOT NULL DEFAULT ''")


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
            payload = json.loads(row["payload"])
            if payload.get("pass_for"):
                _extend_pass(c, payload["pass_for"], payload.get("plan") or "pro", now)
        return True


def _extend_pass(c, sub: str, plan: str, now: float, days: int = pricing.PASS_DAYS) -> None:
    """Adds days to an account's pass. Days left on another plan are kept, converted at their value
    (10 Essentiel days left become 6 Pro days): changing plan never loses nor gains money."""
    acc = c.execute("SELECT pass_until, plan FROM accounts WHERE sub = ?", (sub,)).fetchone()
    if acc is None:
        return
    left = max(0.0, acc["pass_until"] - now)
    old = acc["plan"] or "pro"
    if left and old != plan:
        left = left * pricing.PLANS[old]["amount"] / pricing.PLANS[plan]["amount"]
    c.execute("UPDATE accounts SET pass_until = ?, plan = ? WHERE sub = ?", (now + left + days * 86400, plan, sub))


def give_pass(sub: str, plan: str, days: int) -> None:
    """The team offers days (a payment that went wrong, a partner…)."""
    with connect() as c:
        _extend_pass(c, sub, plan, time.time(), days)


def day_start(now: float | None = None) -> float:
    """Midnight in Cameroon (UTC+1): the daily limits start again."""
    now = now or time.time()
    return (now + 3600) // 86400 * 86400 - 3600


def unlocked_today(sub: str, now: float | None = None) -> int:
    """Documents this account's pass unlocked since midnight (see grant: trans_id "pass:<sub>")."""
    with connect() as c:
        row = c.execute("SELECT COUNT(*) AS n FROM orders WHERE trans_id = ? AND paid_at >= ?", (f"pass:{sub}", day_start(now))).fetchone()
    return int(row["n"])


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


def account_by_email(email: str) -> dict | None:
    with connect() as c:
        row = c.execute("SELECT * FROM accounts WHERE email = ?", (email.lower(),)).fetchone()
    return dict(row) if row else None


def set_product(order_id: str, product: str, amount: int) -> None:
    """Price follows the document size, but never changes once paid or pending."""
    with connect() as c:
        c.execute(
            "UPDATE orders SET product = ?, amount = ? WHERE id = ? AND status NOT IN ('PAID', 'PENDING')",
            (product, amount, order_id),
        )


def add_event(sid: str, step: str, src: str) -> None:
    """Counts a visitor once per step (the browser may send the same step again)."""
    now = time.time()
    with connect() as c:
        c.execute(
            "INSERT INTO events (sid, step, src, day, ts) VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING",
            (sid, step, src, time.strftime("%Y-%m-%d", time.gmtime(now + 3600)), now),  # Cameroon day (UTC+1)
        )


def funnel(since_day: str) -> list[dict]:
    """Visitors per day, source and step, from since_day (YYYY-MM-DD) on."""
    with connect() as c:
        rows = c.execute(
            "SELECT day, src, step, COUNT(*) AS n FROM events WHERE day >= ? GROUP BY day, src, step ORDER BY day",
            (since_day,),
        ).fetchall()
    return [dict(r) for r in rows]


def purge_events(now: float | None = None) -> None:
    """Visit statistics are kept 12 months (privacy policy)."""
    with connect() as c:
        c.execute("DELETE FROM events WHERE ts < ?", ((now or time.time()) - 365 * 86400,))


# ------------------------------------------------------------------ support

def create_ticket(sub: str | None, name: str, contact: str, order_id: str | None, body: str) -> str:
    ticket_id = uuid.uuid4().hex
    now = time.time()
    with connect() as c:
        c.execute(
            "INSERT INTO tickets (id, sub, name, contact, order_id, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (ticket_id, sub, name, contact, order_id, "NEW", now, now),
        )
        c.execute("INSERT INTO ticket_messages (ticket_id, author, body, ts) VALUES (?,?,?,?)", (ticket_id, "client", body, now))
    return ticket_id


def get_ticket(ticket_id: str) -> dict | None:
    with connect() as c:
        row = c.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if row is None:
            return None
        msgs = c.execute("SELECT author, body, ts FROM ticket_messages WHERE ticket_id = ? ORDER BY ts", (ticket_id,)).fetchall()
    return {**dict(row), "messages": [dict(m) for m in msgs]}


def add_message(ticket_id: str, author: str, body: str) -> None:
    """A customer's message puts the ticket back on the team's side; a team answer on the customer's."""
    now = time.time()
    with connect() as c:
        c.execute("INSERT INTO ticket_messages (ticket_id, author, body, ts) VALUES (?,?,?,?)", (ticket_id, author, body, now))
        c.execute("UPDATE tickets SET status = ?, updated_at = ? WHERE id = ?", ("NEW" if author == "client" else "ANSWERED", now, ticket_id))


def set_ticket_status(ticket_id: str, status: str) -> None:
    with connect() as c:
        c.execute("UPDATE tickets SET status = ?, updated_at = ? WHERE id = ?", (status, time.time(), ticket_id))


def list_tickets(sub: str | None = None, limit: int = 200) -> list[dict]:
    """Newest activity first, with the last message (all tickets for the team, or one customer's)."""
    where, params = ("WHERE t.sub = ?", (sub,)) if sub else ("", ())
    with connect() as c:
        rows = c.execute(
            "SELECT t.*, (SELECT body FROM ticket_messages m WHERE m.ticket_id = t.id ORDER BY ts DESC LIMIT 1) AS last, "
            "(SELECT author FROM ticket_messages m WHERE m.ticket_id = t.id ORDER BY ts DESC LIMIT 1) AS last_author "
            f"FROM tickets t {where} ORDER BY t.updated_at DESC LIMIT {int(limit)}",
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def purge_tickets(now: float | None = None) -> None:
    """Support conversations are kept 12 months after their last message (privacy policy)."""
    limit = (now or time.time()) - 365 * 86400
    with connect() as c:
        c.execute("DELETE FROM ticket_messages WHERE ticket_id IN (SELECT id FROM tickets WHERE updated_at < ?)", (limit,))
        c.execute("DELETE FROM tickets WHERE updated_at < ?", (limit,))
