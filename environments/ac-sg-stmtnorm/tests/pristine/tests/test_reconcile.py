from decimal import Decimal
from pathlib import Path

from stmtnorm.normalize import read_statement
from stmtnorm.reconcile import check_balances, summarize

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_samples_balance():
    for name in ("aurum_2026-10.csv", "brightwater_2026-10.csv", "corvid_2026-10.txt"):
        assert check_balances(read_statement(SAMPLES / name)) == []


def test_opening_balance_mismatch():
    txns = read_statement(SAMPLES / "corvid_2026-10.txt")
    issues = check_balances(txns, opening=Decimal("990.00"))
    assert [(i.kind, i.line) for i in issues] == [("balance_mismatch", 2)]


def test_summary():
    s = summarize(read_statement(SAMPLES / "aurum_2026-10.csv"))
    assert (s["count"], s["credits"], s["debits"], s["closing"]) == (
        4, Decimal("3450.00"), Decimal("995.20"), Decimal("2454.80"))
