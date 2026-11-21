"""Held-out acceptance tests for LOY-412 (never shown to the agent).

Run by the grader against the agent's loyalty/ package and migrations/ dir,
copied into a scratch project together with this file and old_migrations/.
"""
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from loyalty import members
from loyalty.db import MIGRATIONS_DIR, connect, migrate
from loyalty.ledger import InsufficientPoints, Ledger
from loyalty.statements import statement

HERE = Path(__file__).parent


def lots(conn, member):
    return [dict(r) for r in conn.execute(
        "SELECT earn_txn_id, earned_at, expires_at, original, remaining FROM point_lots "
        "WHERE member_id = ? ORDER BY id", (member,))]


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "h.db")
    migrate(c)
    for mid in ("A", "B"):
        members.enroll(c, mid, mid, "2024-01-01T00:00:00Z")
    yield c
    c.close()


def old_db(tmp_path):
    """A database at schema 0002 with history, as production is today."""
    c = connect(tmp_path / "old.db")
    d = tmp_path / "old_migrations"
    shutil.copytree(HERE / "old_migrations", d)
    migrate(c, d)
    return c


def test_expiry_boundary_is_exclusive(conn):
    led = Ledger(conn)
    led.earn("A", 70, "2025-05-05T08:30:00Z")
    assert led.balance("A", "2026-05-05T08:29:59Z") == 70
    assert led.balance("A", "2026-05-05T08:30:00Z") == 0


def test_non_utc_input_normalised(conn):
    led = Ledger(conn)
    led.earn("A", 10, "2025-05-05T14:00:00+05:30")
    assert lots(conn, "A")[0]["expires_at"] == "2026-05-05T08:30:00Z"


def test_redeem_skips_expired_lot(conn):
    led = Ledger(conn)
    led.earn("A", 100, "2025-01-01T00:00:00Z")
    led.earn("A", 100, "2025-06-01T00:00:00Z")
    led.redeem("A", 80, "2026-02-01T00:00:00Z")
    assert [l["remaining"] for l in lots(conn, "A")] == [100, 20]


def test_tie_breaks_on_lot_id(conn):
    led = Ledger(conn)
    led.earn("A", 30, "2025-03-01T00:00:00Z")
    led.earn("A", 30, "2025-03-01T00:00:00Z")
    led.redeem("A", 40, "2025-04-01T00:00:00Z")
    assert [l["remaining"] for l in lots(conn, "A")] == [0, 20]


def test_insufficient_changes_nothing(conn):
    led = Ledger(conn)
    led.earn("A", 50, "2025-01-01T00:00:00Z")
    led.earn("A", 20, "2025-12-01T00:00:00Z")
    before = lots(conn, "A")
    n = conn.execute("SELECT count(*) FROM transactions").fetchone()[0]
    with pytest.raises(InsufficientPoints):
        led.redeem("A", 21, "2026-01-02T00:00:00Z")
    assert lots(conn, "A") == before
    assert conn.execute("SELECT count(*) FROM transactions").fetchone()[0] == n


def test_expire_due_all_members_idempotent(conn):
    led = Ledger(conn)
    led.earn("A", 40, "2025-01-10T00:00:00Z")
    led.earn("B", 25, "2025-02-10T00:00:00Z")
    led.earn("B", 5, "2025-08-10T00:00:00Z")
    led.redeem("B", 10, "2025-03-01T00:00:00Z")
    assert led.expire_due("2026-02-15T00:00:00Z") == 55
    assert led.expire_due("2026-02-15T00:00:00Z") == 0
    assert led.expire_due("2026-09-01T00:00:00Z") == 5
    exp = conn.execute("SELECT member_id, points, at FROM transactions WHERE kind='expire' "
                       "ORDER BY at").fetchall()
    assert [tuple(r) for r in exp] == [("A", -40, "2026-01-10T00:00:00Z"),
                                       ("B", -15, "2026-02-10T00:00:00Z"),
                                       ("B", -5, "2026-08-10T00:00:00Z")]
    assert led.balance("B", "2026-09-02T00:00:00Z") == 0


def test_statement_buckets(conn):
    led = Ledger(conn)
    led.earn("A", 90, "2025-03-15T00:00:00Z")
    led.earn("A", 10, "2026-03-02T00:00:00Z")
    led.redeem("A", 30, "2026-03-10T00:00:00Z")
    led.expire_due("2026-04-01T00:00:00Z")
    s = statement(conn, "A", 2026, 3)
    assert (s["opening"], s["earned"], s["redeemed"], s["expired"], s["closing"]) == (90, 10, 30, 60, 10)


def test_purchase_creates_lot(conn):
    members.award_purchase(conn, "A", 5000, "2025-07-01T00:00:00Z")
    assert lots(conn, "A")[0]["original"] == 50


def test_migration_on_production_shaped_db(tmp_path):
    c = old_db(tmp_path)
    members.enroll(c, "P", "Prod", "2023-01-01T00:00:00Z")
    members.enroll(c, "Q", "Prod2", "2023-01-01T00:00:00Z")
    c.executemany("INSERT INTO transactions (member_id, kind, points, at, ref) VALUES (?,?,?,?,?)", [
        ("P", "earn", 100, "2023-02-01T00:00:00Z", "o1"),
        ("Q", "earn", 500, "2023-02-02T00:00:00Z", "o2"),
        ("P", "earn", 60, "2024-01-15T00:00:00Z", "o3"),
        ("P", "redeem", -120, "2024-03-01T00:00:00Z", "r1"),   # 100-lot expired 2024-02-01
        ("Q", "redeem", -200, "2023-06-01T00:00:00Z", "r2"),
    ])
    c.commit()
    ids_before = [tuple(r) for r in c.execute("SELECT id, member_id, kind, points, at, ref FROM transactions ORDER BY id")]
    migrate(c)  # agent's migrations/ (0003)
    assert [tuple(r) for r in c.execute("SELECT id, member_id, kind, points, at, ref FROM transactions ORDER BY id")] == ids_before
    # 60-lot pays 60 (unexpired); 60 shortfall grandfathered from the expired 100-lot
    assert [l["remaining"] for l in lots(c, "P")] == [40, 0]
    assert [l["remaining"] for l in lots(c, "Q")] == [300]
    assert lots(c, "P")[0]["earn_txn_id"] == ids_before[0][0]
    c.execute("INSERT INTO transactions (member_id, kind, points, at) VALUES ('P', 'expire', -1, '2025-01-01T00:00:00Z')")
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("INSERT INTO transactions (member_id, kind, points, at) VALUES ('P', 'bogus', 1, '2025-01-01T00:00:00Z')")
    assert c.execute("PRAGMA foreign_key_check").fetchall() == []
    assert "0003" in {r[0] for r in c.execute("SELECT version FROM schema_migrations")}


def test_migration_on_dev_snapshot(tmp_path):
    snap = HERE / "dev_snapshot.db"
    if not snap.exists():
        pytest.skip("no dev snapshot")
    db = tmp_path / "snap.db"
    shutil.copy(snap, db)
    c = connect(db)
    totals = {r[0]: r[1] for r in c.execute("SELECT member_id, SUM(points) FROM transactions GROUP BY member_id")}
    migrate(c)
    lot_totals = {r[0]: r[1] for r in c.execute("SELECT member_id, SUM(remaining) FROM point_lots GROUP BY member_id")}
    assert lot_totals == totals


def test_cli_after_migrate(tmp_path):
    db = tmp_path / "cli.db"
    run = lambda *a: subprocess.run([sys.executable, "-m", "loyalty", "--db", str(db), *a],
                                    capture_output=True, text=True, cwd=HERE.parent)
    assert run("migrate").returncode == 0
    assert run("enroll", "Z", "Zed", "--at", "2025-01-01T00:00:00Z").returncode == 0
    assert run("earn", "Z", "10", "--at", "2025-01-02T00:00:00Z").returncode == 0
    out = run("balance", "Z", "--at", "2026-01-02T00:00:00Z")
    assert out.stdout.strip() == "0"
