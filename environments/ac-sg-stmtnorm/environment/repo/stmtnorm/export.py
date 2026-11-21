"""Output formats: JSON (default), CSV, and an hledger-style journal."""
from __future__ import annotations

import csv
import io
import json

from .amounts import fmt_amount
from .normalize import Transaction

FIELDS = ("date", "description", "amount", "balance")


def to_records(txns: list[Transaction]) -> list[dict]:
    return [{"date": t.date.isoformat(), "description": t.description,
             "amount": fmt_amount(t.amount),
             "balance": fmt_amount(t.balance) if t.balance is not None else None}
            for t in txns]


def to_json(txns: list[Transaction]) -> str:
    return json.dumps(to_records(txns), indent=2, ensure_ascii=False)


def to_csv(txns: list[Transaction]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for rec in to_records(txns):
        writer.writerow({k: "" if v is None else v for k, v in rec.items()})
    return buf.getvalue()


def to_ledger(txns: list[Transaction], account: str = "Assets:Bank",
              income: str = "Income:Unclassified", expense: str = "Expenses:Unclassified") -> str:
    blocks = []
    for t in txns:
        contra = income if t.amount > 0 else expense
        lines = [f"{t.date.isoformat()} {t.description}",
                 f"    {account:<36}{fmt_amount(t.amount):>12}",
                 f"    {contra}"]
        if t.balance is not None:
            lines[1] += f" = {fmt_amount(t.balance)}"
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + ("\n" if blocks else "")
