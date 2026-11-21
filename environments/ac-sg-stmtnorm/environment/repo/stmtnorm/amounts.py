"""Parsing money amounts as banks print them."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

CURRENCY_SYMBOLS = "$£€"


class AmountError(ValueError):
    pass


def parse_amount(text: str, decimal_sep: str = ".", thousands_sep: str = ",") -> Decimal:
    """Parse "1,234.56", "(45.00)", "45.00-", "-£3.10", "1.234,56" (with the
    matching separators) into a Decimal. Empty input is an error."""
    raw = text.strip()
    if not raw:
        raise AmountError("empty amount")
    negative = False
    if raw.startswith("(") and raw.endswith(")"):
        negative, raw = True, raw[1:-1].strip()
    if raw.endswith("-"):
        negative, raw = not negative, raw[:-1].strip()
    if raw.startswith("-"):
        negative, raw = not negative, raw[1:].strip()
    elif raw.startswith("+"):
        raw = raw[1:].strip()
    raw = raw.lstrip(CURRENCY_SYMBOLS).strip()
    if thousands_sep:
        groups = raw.split(decimal_sep)[0].split(thousands_sep)
        if len(groups) > 1 and (not groups[0] or any(len(g) != 3 for g in groups[1:])):
            raise AmountError(f"bad digit grouping in {text!r}")
        raw = raw.replace(thousands_sep, "")
    if decimal_sep != ".":
        raw = raw.replace(decimal_sep, ".")
    if not re.fullmatch(r"\d+(\.\d{1,2})?", raw):
        raise AmountError(f"not an amount: {text!r}")
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise AmountError(f"not an amount: {text!r}") from None
    return -value if negative else value


def fmt_amount(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01')):f}"
