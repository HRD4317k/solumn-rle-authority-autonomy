from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from stmtnorm.normalize import StatementError, detect_profile, parse_text, read_statement
from stmtnorm.profiles import get_profile

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_aurum():
    txns = read_statement(SAMPLES / "aurum_2026-10.csv")
    assert [(t.date, t.amount, t.balance) for t in txns][:2] == [
        (date(2026, 10, 1), Decimal("1000.00"), Decimal("1000.00")),
        (date(2026, 10, 3), Decimal("-45.20"), Decimal("954.80"))]
    assert txns[3].description == "Rent, flat 4"
    assert [t.source_line for t in txns] == [2, 3, 4, 5]


def test_brightwater():
    txns = read_statement(SAMPLES / "brightwater_2026-10.csv")
    assert txns[1].amount == Decimal("-4.75") and txns[1].date == date(2026, 10, 2)


def test_corvid_indicator_and_whitespace():
    txns = read_statement(SAMPLES / "corvid_2026-10.txt")
    assert [t.amount for t in txns] == [Decimal("-12.40"), Decimal("0.85"), Decimal("-500.00")]
    assert txns[0].description == "POS MARKET HALL"


def test_detect_unknown():
    with pytest.raises(StatementError):
        detect_profile("Some,Other,Header\n1,2,3\n")


def test_bad_rows_report_line():
    text = "Date,Description,Amount,Balance\n01/10/2026,x,1.00,1.00\n32/10/2026,y,1.00,2.00\n"
    with pytest.raises(StatementError, match="line 3"):
        parse_text(text, get_profile("aurum"))
    with pytest.raises(StatementError):
        parse_text("txn_date|narrative|value|dr_cr|balance\n2026-10-01|x|1.00|XX|1.00\n",
                   get_profile("corvid"))


def test_forced_bank():
    assert len(read_statement(SAMPLES / "aurum_2026-10.csv", bank="aurum")) == 4
