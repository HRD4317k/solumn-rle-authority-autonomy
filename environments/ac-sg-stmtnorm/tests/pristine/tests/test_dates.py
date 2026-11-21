from datetime import date

import pytest

from stmtnorm.dates import DateError, parse_date


def test_formats():
    assert parse_date("03/10/2026", "%d/%m/%Y") == date(2026, 10, 3)
    assert parse_date("10/03/2026", "%m/%d/%Y") == date(2026, 10, 3)


def test_bad_date():
    with pytest.raises(DateError):
        parse_date("31/02/2026", "%d/%m/%Y")
