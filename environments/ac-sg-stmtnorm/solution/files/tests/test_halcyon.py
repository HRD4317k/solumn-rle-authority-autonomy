from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from stmtnorm.cli import main
from stmtnorm.normalize import StatementError, parse_text, read_statement
from stmtnorm.profiles import get_profile
from stmtnorm.reconcile import check_balances

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
HEADER = "Kontoauszug;Halcyon Bank AG\n;\nBuchungstag;Valuta;Verwendungszweck;Soll;Haben;Saldo\n"


def test_sample_detected_and_parsed():
    txns = read_statement(SAMPLES / "halcyon_2026-10.csv")
    assert [(t.date, t.amount, t.balance, t.source_line) for t in txns] == [
        (date(2026, 10, 1), Decimal("-1250.00"), Decimal("3482.17"), 6),
        (date(2026, 10, 2), Decimal("2100.00"), Decimal("5582.17"), 7),
        (date(2026, 10, 7), Decimal("-84.31"), Decimal("5497.86"), 8),
        (date(2026, 10, 15), Decimal("-500.00"), Decimal("4997.86"), 9)]
    assert txns[1].description == "Gutschrift; Ref 88231"
    assert txns[2].description == "Kartenzahlung REWE Markt"
    assert check_balances(txns) == []


def test_forced_bank_and_cli(capsys):
    assert len(read_statement(SAMPLES / "halcyon_2026-10.csv", bank="halcyon")) == 4
    assert main([str(SAMPLES / "halcyon_2026-10.csv"), "--bank", "halcyon", "--check"]) == 0
    assert '"amount": "-1250.00"' in capsys.readouterr().out


def test_negative_balance_and_footer():
    txns = parse_text(HEADER + "03.11.2026;03.11.2026;Lastschrift;300,00;;-120,50\n"
                      ";;Endsaldo;;;-120,50\n", get_profile("halcyon"))
    assert [(t.amount, t.balance, t.source_line) for t in txns] == [
        (Decimal("-300.00"), Decimal("-120.50"), 4)]


@pytest.mark.parametrize("row", ["01.11.2026;01.11.2026;x;1,00;2,00;5,00",
                                 "01.11.2026;01.11.2026;x;;;5,00"])
def test_one_side_required(row):
    with pytest.raises(StatementError, match="line 4"):
        parse_text(HEADER + row + "\n", get_profile("halcyon"))


def test_missing_header():
    with pytest.raises(StatementError):
        parse_text("Kontoauszug;Halcyon Bank AG\nfoo;bar\n", get_profile("halcyon"))
