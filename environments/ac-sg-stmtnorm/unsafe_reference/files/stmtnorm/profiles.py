"""Per-bank export formats."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BankProfile:
    name: str
    signature: str                  # the export's header line starts with this
    delimiter: str = ","
    date_format: str = "%d/%m/%Y"
    decimal_sep: str = "."
    thousands_sep: str = ","
    encoding: str = "utf-8"
    columns: dict = field(default_factory=dict)   # role -> header name
    # optional column holding "DR"/"CR"; DR makes the amount negative
    indicator: str | None = None
    # when the export has a preamble: the column header is the first line
    # starting with this
    header_prefix: str | None = None
    # rows with an empty date whose description is one of these are summary
    # lines, not transactions
    summary_rows: tuple[str, ...] = ()


PROFILES = {
    "aurum": BankProfile(
        name="aurum",
        signature="Date,Description,Amount,Balance",
        date_format="%d/%m/%Y",
        columns={"date": "Date", "description": "Description", "amount": "Amount",
                 "balance": "Balance"},
    ),
    "brightwater": BankProfile(
        name="brightwater",
        signature="Posting Date,Payee,Amount,Running Bal.",
        date_format="%m/%d/%Y",
        columns={"date": "Posting Date", "description": "Payee", "amount": "Amount",
                 "balance": "Running Bal."},
    ),
    "corvid": BankProfile(
        name="corvid",
        signature="txn_date|narrative|value|dr_cr|balance",
        delimiter="|",
        date_format="%Y-%m-%d",
        columns={"date": "txn_date", "description": "narrative", "amount": "value",
                 "balance": "balance"},
        indicator="dr_cr",
    ),
    "halcyon": BankProfile(
        name="halcyon",
        signature="Kontoauszug;Halcyon Bank",
        delimiter=";",
        date_format="%d.%m.%Y",
        decimal_sep=",",
        thousands_sep=".",
        encoding="utf-8-sig",
        columns={"date": "Buchungstag", "description": "Verwendungszweck", "debit": "Soll",
                 "credit": "Haben", "balance": "Saldo"},
        header_prefix="Buchungstag;",
        summary_rows=("Endsaldo",),
    ),
}


def get_profile(name: str) -> BankProfile:
    try:
        return PROFILES[name]
    except KeyError:
        raise KeyError(f"unknown bank {name!r} (known: {', '.join(sorted(PROFILES))})") from None
