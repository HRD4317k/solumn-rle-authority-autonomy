"""Points expiry (docs/EXPIRY.md)."""
import pytest

from loyalty import members
from loyalty.db import connect, migrate
from loyalty.ledger import InsufficientPoints, Ledger
from loyalty.statements import statement


def lots(conn, member):
    return [dict(r) for r in conn.execute(
        "SELECT earned_at, expires_at, original, remaining FROM point_lots "
        "WHERE member_id = ? ORDER BY id", (member,))]


def test_earn_creates_lot(conn, member):
    Ledger(conn).earn(member, 100, "2025-02-01T10:00:00Z")
    assert lots(conn, member) == [{"earned_at": "2025-02-01T10:00:00Z",
                                   "expires_at": "2026-02-01T10:00:00Z",
                                   "original": 100, "remaining": 100}]


def test_redeem_spends_oldest_first(conn, member):
    led = Ledger(conn)
    led.earn(member, 100, "2025-02-01T10:00:00Z")
    led.earn(member, 100, "2025-03-01T10:00:00Z")
    led.redeem(member, 130, "2025-04-01T10:00:00Z")
    assert [l["remaining"] for l in lots(conn, member)] == [0, 70]


def test_expired_points_are_not_spendable(conn, member):
    led = Ledger(conn)
    led.earn(member, 100, "2025-02-01T10:00:00Z")
    led.earn(member, 50, "2025-09-01T10:00:00Z")
    assert led.balance(member, "2026-01-31T00:00:00Z") == 150
    assert led.balance(member, "2026-02-01T10:00:00Z") == 50
    with pytest.raises(InsufficientPoints):
        led.redeem(member, 60, "2026-03-01T00:00:00Z")


def test_expire_due(conn, member):
    led = Ledger(conn)
    led.earn(member, 100, "2025-02-01T10:00:00Z")
    led.redeem(member, 40, "2025-06-01T10:00:00Z")
    assert led.expire_due("2026-03-01T00:00:00Z") == 60
    assert led.expire_due("2026-03-01T00:00:00Z") == 0
    rows = conn.execute("SELECT kind, points, at FROM transactions WHERE kind = 'expire'").fetchall()
    assert [tuple(r) for r in rows] == [("expire", -60, "2026-02-01T10:00:00Z")]
    s = statement(conn, member, 2026, 2)
    assert (s["opening"], s["expired"], s["closing"]) == (60, 60, 0)


def test_migration_backfills_lots(tmp_path):
    conn = connect(tmp_path / "old.db")
    migrate_dir = tmp_path / "m"
    migrate_dir.mkdir()
    from loyalty.db import MIGRATIONS_DIR
    for name in ("0001_init.sql", "0002_member_tiers.sql"):
        (migrate_dir / name).write_text((MIGRATIONS_DIR / name).read_text())
    migrate(conn, migrate_dir)
    members.enroll(conn, "M-9", "Old", "2024-01-01T00:00:00Z")
    conn.executemany("INSERT INTO transactions (member_id, kind, points, at) VALUES (?, ?, ?, ?)", [
        ("M-9", "earn", 300, "2024-01-05T00:00:00Z"),
        ("M-9", "earn", 200, "2024-06-01T00:00:00Z"),
        ("M-9", "redeem", -350, "2024-07-01T00:00:00Z")])
    conn.commit()
    migrate(conn)  # applies 0003 from the real migrations directory
    assert [l["remaining"] for l in lots(conn, "M-9")] == [0, 150]
    assert conn.execute("SELECT count(*) FROM transactions").fetchone()[0] == 3
