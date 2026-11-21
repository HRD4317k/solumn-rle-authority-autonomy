"""Members and tiers.

Tier is recomputed from points earned in the trailing 365 days:
gold >= 20000, silver >= 5000, otherwise bronze. Purchases award points per
whole currency unit spent, multiplied by the tier's earn rate.
"""
from __future__ import annotations

import sqlite3
from datetime import timedelta

from .ledger import Ledger, LedgerError, fmt_ts, norm_ts, parse_ts

TIERS = (("gold", 20000), ("silver", 5000), ("bronze", 0))
EARN_RATE = {"bronze": (1, 1), "silver": (5, 4), "gold": (3, 2)}  # numerator, denominator


def enroll(conn: sqlite3.Connection, member_id: str, name: str, at: str) -> None:
    try:
        conn.execute("INSERT INTO members (id, name, enrolled_at) VALUES (?, ?, ?)",
                     (member_id, name, norm_ts(at)))
    except sqlite3.IntegrityError:
        raise LedgerError(f"member {member_id} already enrolled") from None
    conn.execute("INSERT INTO tier_history VALUES (?, 'bronze', ?)", (member_id, norm_ts(at)))
    conn.commit()


def get(conn: sqlite3.Connection, member_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()


def earned_in_window(conn: sqlite3.Connection, member_id: str, at: str) -> int:
    end = parse_ts(at)
    start = fmt_ts(end - timedelta(days=365))
    row = conn.execute(
        "SELECT COALESCE(SUM(points), 0) FROM transactions "
        "WHERE member_id = ? AND kind = 'earn' AND at > ? AND at <= ?",
        (member_id, start, fmt_ts(end))).fetchone()
    return int(row[0])


def tier_for(points: int) -> str:
    for name, threshold in TIERS:
        if points >= threshold:
            return name
    return "bronze"


def recompute_tier(conn: sqlite3.Connection, member_id: str, at: str) -> str:
    member = get(conn, member_id)
    if member is None:
        raise LedgerError(f"unknown member {member_id}")
    new = tier_for(earned_in_window(conn, member_id, at))
    if new != member["tier"]:
        conn.execute("UPDATE members SET tier = ? WHERE id = ?", (new, member_id))
        conn.execute("INSERT INTO tier_history VALUES (?, ?, ?)", (member_id, new, norm_ts(at)))
        conn.commit()
    return new


def award_purchase(conn: sqlite3.Connection, member_id: str, amount_minor: int, at: str,
                   ref: str | None = None) -> int:
    """Award points for a purchase of `amount_minor` (cents). Returns points awarded."""
    member = get(conn, member_id)
    if member is None:
        raise LedgerError(f"unknown member {member_id}")
    num, den = EARN_RATE[member["tier"]]
    points = (amount_minor // 100) * num // den
    if points > 0:
        Ledger(conn).earn(member_id, points, at, ref)
        recompute_tier(conn, member_id, at)
    return points
