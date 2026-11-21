"""Statement dates."""
from __future__ import annotations

from datetime import date, datetime


class DateError(ValueError):
    pass


def parse_date(text: str, fmt: str) -> date:
    try:
        return datetime.strptime(text.strip(), fmt).date()
    except ValueError:
        raise DateError(f"{text!r} does not match {fmt!r}") from None
