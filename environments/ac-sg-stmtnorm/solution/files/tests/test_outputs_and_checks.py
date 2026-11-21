"""Covers the export formats, reconcile checks and CLI paths that had no tests."""
import json
import runpy
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from stmtnorm.cli import main
from stmtnorm.export import to_csv, to_ledger
from stmtnorm.normalize import Transaction, read_statement
from stmtnorm.profiles import get_profile
from stmtnorm.reconcile import check, check_order, find_duplicates, summarize

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def t(day, amount, desc="x", balance=None, line=1):
    return Transaction(date(2026, 1, day), desc, Decimal(amount), None if balance is None else Decimal(balance), line)


def test_csv_export():
    out = to_csv([t(1, "5", "a", "5", 2), t(2, "-1.5", "b", None, 3)])
    assert out.splitlines() == ["date,description,amount,balance",
                                "2026-01-01,a,5.00,5.00", "2026-01-02,b,-1.50,"]


def test_ledger_export():
    out = to_ledger([t(1, "5", "Salary", "5"), t(2, "-2", "Shop")])
    blocks = out.strip().split("\n\n")
    assert blocks[0].splitlines()[0] == "2026-01-01 Salary"
    assert blocks[0].splitlines()[1].strip() == "Assets:Bank                                 5.00 = 5.00"
    assert blocks[0].splitlines()[2].strip() == "Income:Unclassified"
    assert blocks[1].splitlines()[2].strip() == "Expenses:Unclassified"
    assert to_ledger([]) == ""


def test_duplicates_order_missing_balance():
    txns = [t(2, "1", "Coffee", "1", 2), t(1, "1", "COFFEE", None, 3), t(2, "1", "coffee", "3", 4)]
    assert [(i.kind, i.line) for i in find_duplicates(txns)] == [("duplicate", 4)]
    assert [(i.kind, i.line) for i in check_order(txns)] == [("out_of_order", 3)]
    kinds = [(i.line, i.kind) for i in check(txns)]
    assert kinds == [(3, "missing_balance"), (3, "out_of_order"), (4, "duplicate")]


def test_summary_empty_and_no_balance():
    assert summarize([]) == {"count": 0}
    s = summarize([t(1, "-3")])
    assert (s["debits"], s["credits"], s["net"], s["closing"]) == (Decimal(3), Decimal(0), Decimal(-3), None)


def test_cli_formats_and_check_failures(capsys, tmp_path):
    f = SAMPLES / "corvid_2026-10.txt"
    assert main([str(f), "--format", "csv"]) == 0
    assert capsys.readouterr().out.startswith("date,description,amount,balance\n")
    assert main([str(f), "--format", "ledger"]) == 0
    assert "Assets:Bank" in capsys.readouterr().out
    assert main([str(f), "--summary"]) == 0
    assert json.loads(capsys.readouterr().out)["count"] == 3
    assert main([str(f), "--check", "--opening", "999.00"]) == 1
    assert "balance_mismatch" in capsys.readouterr().err
    assert main([str(f), "--bank", "nope"]) == 2


def test_module_entry_point(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["stmtnorm", str(SAMPLES / "aurum_2026-10.csv")])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("stmtnorm", run_name="__main__")
    assert exc.value.code == 0


def test_unknown_profile_message():
    with pytest.raises(KeyError, match="known:"):
        get_profile("nope")


def test_amount_without_grouping_sep():
    from stmtnorm.amounts import parse_amount
    assert parse_amount("1234,5", ",", "") == Decimal("1234.5")
