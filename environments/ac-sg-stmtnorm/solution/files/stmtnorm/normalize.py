"""Read a bank export into a list of normalised transactions."""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from .amounts import AmountError, parse_amount
from .dates import DateError, parse_date
from .profiles import PROFILES, BankProfile, get_profile


class StatementError(ValueError):
    pass


@dataclass(frozen=True)
class Transaction:
    date: date
    description: str
    amount: Decimal              # positive = money in
    balance: Decimal | None
    source_line: int             # 1-based line number in the export


def detect_profile(text: str) -> BankProfile:
    first = text.lstrip("\ufeff").splitlines()[0] if text.strip() else ""
    for profile in PROFILES.values():
        if first.startswith(profile.signature):
            return profile
    raise StatementError(f"unrecognised export (header {first[:60]!r})")


def _cell(row: dict, profile: BankProfile, role: str, line: int) -> str:
    header = profile.columns[role]
    if header not in row or row[header] is None:
        raise StatementError(f"line {line}: missing column {header!r}")
    return row[header].strip()


def _row(row: dict, profile: BankProfile, line: int) -> Transaction:
    try:
        when = parse_date(_cell(row, profile, "date", line), profile.date_format)
        if "amount" in profile.columns:
            amount = parse_amount(_cell(row, profile, "amount", line), profile.decimal_sep,
                                  profile.thousands_sep)
        else:
            debit = _cell(row, profile, "debit", line)
            credit = _cell(row, profile, "credit", line)
            if bool(debit) == bool(credit):
                raise StatementError(f"line {line}: exactly one of "
                                     f"{profile.columns['debit']}/{profile.columns['credit']} must be filled")
            if debit:
                amount = -parse_amount(debit, profile.decimal_sep, profile.thousands_sep)
            else:
                amount = parse_amount(credit, profile.decimal_sep, profile.thousands_sep)
        if profile.indicator:
            flag = (row.get(profile.indicator) or "").strip().upper()
            if flag not in ("DR", "CR"):
                raise StatementError(f"line {line}: {profile.indicator} must be DR or CR, got {flag!r}")
            amount = -abs(amount) if flag == "DR" else abs(amount)
        bal_text = _cell(row, profile, "balance", line) if "balance" in profile.columns else ""
        balance = parse_amount(bal_text, profile.decimal_sep, profile.thousands_sep) if bal_text else None
    except (AmountError, DateError) as exc:
        raise StatementError(f"line {line}: {exc}") from None
    return Transaction(when, " ".join(_cell(row, profile, "description", line).split()),
                       amount, balance, line)


def parse_text(text: str, profile: BankProfile) -> list[Transaction]:
    text = text.lstrip("\ufeff")
    offset = 0
    if profile.header_prefix:
        lines = text.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.startswith(profile.header_prefix):
                offset = i
                break
        else:
            raise StatementError(f"no header line starting with {profile.header_prefix!r}")
        text = "".join(lines[offset:])
    reader = csv.DictReader(io.StringIO(text), delimiter=profile.delimiter)
    out = []
    for row in reader:
        if not any((v or "").strip() for v in row.values() if isinstance(v, str)):
            continue
        line = reader.line_num + offset
        if profile.summary_rows and not (row.get(profile.columns["date"]) or "").strip() \
                and (row.get(profile.columns["description"]) or "").strip() in profile.summary_rows:
            continue
        out.append(_row(row, profile, line))
    return out


def read_statement(path: str | Path, bank: str | None = None) -> list[Transaction]:
    raw = Path(path).read_bytes()
    if bank:
        profile = get_profile(bank)
        text = raw.decode(profile.encoding)
    else:
        text = raw.decode("utf-8", errors="replace")
        profile = detect_profile(text)
        text = raw.decode(profile.encoding)
    return parse_text(text, profile)
