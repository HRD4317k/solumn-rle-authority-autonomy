from decimal import Decimal

import pytest

from stmtnorm.amounts import AmountError, fmt_amount, parse_amount


@pytest.mark.parametrize("text,expected", [
    ("12.40", "12.40"), ("1,234.56", "1234.56"), ("-45.20", "-45.20"), ("(4.75)", "-4.75"),
    ("$3,100.00", "3100.00"), ("($120.10)", "-120.10"), ("45.00-", "-45.00"), ("+7", "7"),
    ("£0.99", "0.99"), ("1,000,000.00", "1000000.00"),
])
def test_parse_amount(text, expected):
    assert parse_amount(text) == Decimal(expected)


def test_european_separators():
    assert parse_amount("1.234,56", ",", ".") == Decimal("1234.56")
    assert parse_amount("-120,50", ",", ".") == Decimal("-120.50")


@pytest.mark.parametrize("bad", ["", "  ", "12.345", "1,23.00", "abc", "1.2.3", ",100.00"])
def test_rejects(bad):
    with pytest.raises(AmountError):
        parse_amount(bad)


def test_fmt_amount():
    assert fmt_amount(Decimal("5")) == "5.00"
    assert fmt_amount(Decimal("-0.5")) == "-0.50"
