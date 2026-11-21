from loyalty.ledger import Ledger
from loyalty.statements import render, statement


def test_monthly_statement(conn, member):
    led = Ledger(conn)
    led.earn(member, 500, "2025-03-28T09:00:00Z")
    led.earn(member, 200, "2025-04-02T09:00:00Z")
    led.redeem(member, 120, "2025-04-20T09:00:00Z", ref="ORD-7")
    led.earn(member, 40, "2025-05-01T00:00:00Z")
    s = statement(conn, member, 2025, 4)
    assert (s["opening"], s["earned"], s["redeemed"], s["closing"]) == (500, 200, 120, 580)
    assert [l["kind"] for l in s["lines"]] == ["earn", "redeem"]
    assert "closing balance       580" in render(s)
