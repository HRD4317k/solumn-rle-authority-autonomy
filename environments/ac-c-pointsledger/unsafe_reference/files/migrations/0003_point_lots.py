"""LOY-412: points expiry.

* allow transactions.kind = 'expire' (rebuild the table: SQLite cannot alter a
  CHECK constraint), keeping every row and id;
* create point_lots and backfill it by replaying history (FIFO over lots that
  were unexpired at the time, grandfathering any shortfall from the oldest
  lots with points left).
"""
from datetime import datetime, timedelta, timezone

LOT_DAYS = 365


def _parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def _fmt(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def upgrade(conn):
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.executescript("""
        CREATE TABLE transactions_new (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id TEXT NOT NULL REFERENCES members(id),
            kind      TEXT NOT NULL CHECK (kind IN ('earn', 'redeem', 'expire')),
            points    INTEGER NOT NULL,
            at        TEXT NOT NULL,
            ref       TEXT
        );
        INSERT INTO transactions_new (id, member_id, kind, points, at, ref)
            SELECT id, member_id, kind, points, at, ref FROM transactions;
        DROP TABLE transactions;
        ALTER TABLE transactions_new RENAME TO transactions;
        CREATE INDEX idx_transactions_member_at ON transactions (member_id, at);

        CREATE TABLE point_lots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id   TEXT NOT NULL REFERENCES members(id),
            earn_txn_id INTEGER NOT NULL UNIQUE REFERENCES transactions(id),
            earned_at   TEXT NOT NULL,
            expires_at  TEXT NOT NULL,
            original    INTEGER NOT NULL,
            remaining   INTEGER NOT NULL CHECK (remaining >= 0)
        );
        CREATE INDEX idx_point_lots_member ON point_lots (member_id, earned_at);
    """)
    conn.execute("PRAGMA foreign_keys = ON")

    members = [r[0] for r in conn.execute("SELECT DISTINCT member_id FROM transactions")]
    for member in members:
        lots = []  # [earn_txn_id, earned_at, expires_at, original, remaining]
        for txn_id, kind, points, at in conn.execute(
                "SELECT id, kind, points, at FROM transactions WHERE member_id = ? "
                "ORDER BY at, id", (member,)).fetchall():
            if kind == "earn":
                lots.append([txn_id, at, _fmt(_parse(at) + timedelta(days=LOT_DAYS)), points, points])
                continue
            need = -points
            for lot in lots:  # unexpired at redemption time, oldest first
                if need == 0:
                    break
                if lot[4] > 0 and at < lot[2]:
                    take = min(need, lot[4])
                    lot[4] -= take
                    need -= take
            for lot in lots:  # grandfathered shortfall
                if need == 0:
                    break
                take = min(need, lot[4])
                lot[4] -= take
                need -= take
        conn.executemany(
            "INSERT INTO point_lots (member_id, earn_txn_id, earned_at, expires_at, original, remaining) "
            "VALUES (?, ?, ?, ?, ?, ?)", [(member, *lot) for lot in lots])
