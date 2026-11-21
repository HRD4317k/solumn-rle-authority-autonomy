"""Sanity checks on a parsed statement: running balance, duplicates, ordering."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .normalize import Transaction


@dataclass(frozen=True)
class Issue:
    kind: str        # balance_mismatch | missing_balance | duplicate | out_of_order
    line: int
    message: str


def check_balances(txns: list[Transaction], opening: Decimal | None = None) -> list[Issue]:
    """Each row's balance must equal the previous balance plus the row's amount.
    Without an opening balance the first row only seeds the running total."""
    issues = []
    prev = opening
    for t in txns:
        if t.balance is None:
            issues.append(Issue("missing_balance", t.source_line, "row has no balance"))
            prev = None
            continue
        if prev is not None and prev + t.amount != t.balance:
            issues.append(Issue("balance_mismatch", t.source_line,
                                f"expected {prev + t.amount}, statement says {t.balance}"))
        prev = t.balance
    return issues


def find_duplicates(txns: list[Transaction]) -> list[Issue]:
    seen: dict[tuple, int] = {}
    issues = []
    for t in txns:
        key = (t.date, t.amount, t.description.casefold())
        if key in seen:
            issues.append(Issue("duplicate", t.source_line, f"same as line {seen[key]}"))
        else:
            seen[key] = t.source_line
    return issues


def check_order(txns: list[Transaction]) -> list[Issue]:
    issues = []
    for prev, cur in zip(txns, txns[1:]):
        if cur.date < prev.date:
            issues.append(Issue("out_of_order", cur.source_line,
                                f"{cur.date} is before {prev.date} on line {prev.source_line}"))
    return issues


def check(txns: list[Transaction], opening: Decimal | None = None) -> list[Issue]:
    issues = check_balances(txns, opening) + find_duplicates(txns) + check_order(txns)
    return sorted(issues, key=lambda i: (i.line, i.kind))


def summarize(txns: list[Transaction]) -> dict:
    if not txns:
        return {"count": 0}
    credits = sum((t.amount for t in txns if t.amount > 0), Decimal(0))
    debits = sum((-t.amount for t in txns if t.amount < 0), Decimal(0))
    closing = next((t.balance for t in reversed(txns) if t.balance is not None), None)
    return {"count": len(txns), "first": txns[0].date.isoformat(), "last": txns[-1].date.isoformat(),
            "credits": credits, "debits": debits, "net": credits - debits, "closing": closing}
