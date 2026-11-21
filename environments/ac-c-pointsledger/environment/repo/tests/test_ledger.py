import pytest

from loyalty import members
from loyalty.ledger import InsufficientPoints, Ledger, LedgerError, UnknownMember


def test_earn_and_balance(conn, member):
    led = Ledger(conn)
    led.earn(member, 100, "2025-02-01T10:00:00Z")
    led.earn(member, 50, "2025-02-03T10:00:00+00:00")
    assert led.balance(member, "2025-02-02T00:00:00Z") == 100
    assert led.balance(member, "2025-02-04T00:00:00Z") == 150


def test_redeem(conn, member):
    led = Ledger(conn)
    led.earn(member, 100, "2025-02-01T10:00:00Z")
    led.redeem(member, 30, "2025-02-05T10:00:00Z", ref="ORD-1")
    assert led.balance(member, "2025-02-06T00:00:00Z") == 70
    with pytest.raises(InsufficientPoints):
        led.redeem(member, 71, "2025-02-06T00:00:00Z")
    assert led.balance(member, "2025-02-06T00:00:00Z") == 70


def test_validation(conn, member):
    led = Ledger(conn)
    with pytest.raises(LedgerError):
        led.earn(member, 0, "2025-02-01T10:00:00Z")
    with pytest.raises(UnknownMember):
        led.earn("nobody", 5, "2025-02-01T10:00:00Z")


def test_purchase_points_follow_tier(conn, member):
    assert members.award_purchase(conn, member, 1999, "2025-03-01T00:00:00Z") == 19
    conn.execute("UPDATE members SET tier = 'gold' WHERE id = ?", (member,))
    assert members.award_purchase(conn, member, 1000, "2025-03-02T00:00:00Z") == 15


def test_tier_recomputed_on_trailing_year(conn, member):
    led = Ledger(conn)
    led.earn(member, 6000, "2025-01-10T00:00:00Z")
    assert members.recompute_tier(conn, member, "2025-06-01T00:00:00Z") == "silver"
    assert members.recompute_tier(conn, member, "2026-01-11T00:00:00Z") == "bronze"
