"""The points ledger: every change to a member's points is a transaction row.

Timestamps are UTC ISO-8601 strings with a Z suffix ("2026-03-01T09:30:00Z").
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

LOT_DAYS = 365


class LedgerError(Exception):
    pass


class UnknownMember(LedgerError):
    pass


class InsufficientPoints(LedgerError):
    pass


def parse_ts(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise LedgerError(f"timestamp {value!r} has no timezone")
    return dt.astimezone(timezone.utc)


def fmt_ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def norm_ts(value: str) -> str:
    """Normalise any accepted timestamp to the canonical stored form."""
    return fmt_ts(parse_ts(value))


class Ledger:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _require_member(self, member_id: str) -> None:
        if self.conn.execute("SELECT 1 FROM members WHERE id = ?", (member_id,)).fetchone() is None:
            raise UnknownMember(member_id)

    def _insert(self, member_id: str, kind: str, points: int, at: str, ref: str | None) -> int:
        cur = self.conn.execute(
            "INSERT INTO transactions (member_id, kind, points, at, ref) VALUES (?, ?, ?, ?, ?)",
            (member_id, kind, points, at, ref))
        return cur.lastrowid

    def earn(self, member_id: str, points: int, at: str, ref: str | None = None) -> int:
        if points <= 0:
            raise LedgerError("earned points must be positive")
        self._require_member(member_id)
        at = norm_ts(at)
        txn = self._insert(member_id, "earn", points, at, ref)
        self.conn.execute(
            "INSERT INTO point_lots (member_id, earn_txn_id, earned_at, expires_at, original, remaining) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (member_id, txn, at, fmt_ts(parse_ts(at) + timedelta(days=LOT_DAYS)), points, points))
        self.conn.commit()
        return txn

    def _live_lots(self, member_id: str, at: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT id, remaining FROM point_lots WHERE member_id = ? AND earned_at <= ? "
            "AND expires_at > ? AND remaining > 0 ORDER BY earned_at, id",
            (member_id, at, at)).fetchall()

    def redeem(self, member_id: str, points: int, at: str, ref: str | None = None) -> int:
        if points <= 0:
            raise LedgerError("redeemed points must be positive")
        self._require_member(member_id)
        at = norm_ts(at)
        lots = self._live_lots(member_id, at)
        available = sum(l["remaining"] for l in lots)
        if points > available:
            raise InsufficientPoints(f"{member_id} has {available} points, cannot redeem {points}")
        txn = self._insert(member_id, "redeem", -points, at, ref)
        need = points
        for lot in lots:
            if need == 0:
                break
            take = min(need, lot["remaining"])
            self.conn.execute("UPDATE point_lots SET remaining = remaining - ? WHERE id = ?",
                              (take, lot["id"]))
            need -= take
        self.conn.commit()
        return txn

    def expire_due(self, at: str) -> int:
        """Close out every lot expired at `at` (see docs/EXPIRY.md)."""
        at = norm_ts(at)
        total = 0
        for lot in self.conn.execute(
                "SELECT id, member_id, expires_at, remaining FROM point_lots "
                "WHERE expires_at <= ? AND remaining > 0 ORDER BY expires_at, id", (at,)).fetchall():
            self._insert(lot["member_id"], "expire", -lot["remaining"], lot["expires_at"],
                         f"lot:{lot['id']}")
            self.conn.execute("UPDATE point_lots SET remaining = 0 WHERE id = ?", (lot["id"],))
            total += lot["remaining"]
        self.conn.commit()
        return total

    def balance(self, member_id: str, at: str | None = None) -> int:
        """Spendable points at time `at` (default: now)."""
        self._require_member(member_id)
        at = norm_ts(at) if at else fmt_ts(datetime.now(timezone.utc))
        return sum(l["remaining"] for l in self._live_lots(member_id, at))

    def transactions(self, member_id: str, start: str | None = None,
                     end: str | None = None) -> list[sqlite3.Row]:
        """Transactions with start <= at < end, oldest first."""
        sql = "SELECT * FROM transactions WHERE member_id = ?"
        args: list = [member_id]
        if start:
            sql += " AND at >= ?"
            args.append(norm_ts(start))
        if end:
            sql += " AND at < ?"
            args.append(norm_ts(end))
        return self.conn.execute(sql + " ORDER BY at, id", args).fetchall()
