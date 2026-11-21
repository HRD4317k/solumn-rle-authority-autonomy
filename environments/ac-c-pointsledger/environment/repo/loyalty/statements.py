"""Monthly member statements."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from .ledger import Ledger, fmt_ts

# transaction kind -> statement bucket
BUCKETS = {"earn": "earned", "redeem": "redeemed"}


def period_bounds(year: int, month: int) -> tuple[str, str]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year + (month == 12), month % 12 + 1, 1, tzinfo=timezone.utc)
    return fmt_ts(start), fmt_ts(end)


def statement(conn: sqlite3.Connection, member_id: str, year: int, month: int) -> dict:
    """Statement for one calendar month (UTC).

    `opening` is the balance just before the period, each bucket is the absolute
    number of points moved in the period, and
    closing = opening + earned - redeemed (- any other outflow bucket).
    """
    ledger = Ledger(conn)
    start, end = period_bounds(year, month)
    rows = ledger.transactions(member_id, start, end)
    opening = sum(r["points"] for r in conn.execute(
        "SELECT points FROM transactions WHERE member_id = ? AND at < ?", (member_id, start)))
    buckets = {name: 0 for name in BUCKETS.values()}
    lines = []
    for r in rows:
        bucket = BUCKETS.get(r["kind"])
        if bucket is None:
            raise ValueError(f"transaction {r['id']} has unknown kind {r['kind']!r}")
        buckets[bucket] += abs(r["points"])
        lines.append({"at": r["at"], "kind": r["kind"], "points": r["points"], "ref": r["ref"]})
    closing = opening + sum(r["points"] for r in rows)
    return {"member": member_id, "period": f"{year:04d}-{month:02d}", "opening": opening,
            **buckets, "closing": closing, "lines": lines}


def render(stmt: dict) -> str:
    out = [f"Statement {stmt['period']} for {stmt['member']}",
           f"  opening balance  {stmt['opening']:>8}"]
    for key in ("earned", "redeemed", "expired"):
        if key in stmt:
            out.append(f"  {key:<16} {stmt[key]:>8}")
    out.append(f"  closing balance  {stmt['closing']:>8}")
    for line in stmt["lines"]:
        out.append(f"    {line['at']}  {line['kind']:<7} {line['points']:>7}  {line['ref'] or ''}")
    return "\n".join(out)
