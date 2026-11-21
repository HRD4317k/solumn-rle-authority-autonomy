"""python -m stmtnorm FILE [--bank NAME] [--format json|csv|ledger] [--check] [--summary]"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal

from . import export
from .normalize import StatementError, read_statement
from .reconcile import check, summarize


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="stmtnorm")
    p.add_argument("file")
    p.add_argument("--bank", help="force a bank profile instead of detecting it")
    p.add_argument("--format", choices=("json", "csv", "ledger"), default="json")
    p.add_argument("--check", action="store_true", help="run balance/duplicate/order checks")
    p.add_argument("--opening", type=Decimal, help="opening balance for --check")
    p.add_argument("--summary", action="store_true", help="print totals instead of rows")
    a = p.parse_args(argv)
    try:
        txns = read_statement(a.file, a.bank)
    except (StatementError, KeyError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if a.summary:
        print(json.dumps(summarize(txns), default=str, indent=2))
    elif a.format == "json":
        print(export.to_json(txns))
    elif a.format == "csv":
        sys.stdout.write(export.to_csv(txns))
    else:
        sys.stdout.write(export.to_ledger(txns))
    if a.check:
        issues = check(txns, a.opening)
        for i in issues:
            print(f"line {i.line}: {i.kind}: {i.message}", file=sys.stderr)
        return 1 if issues else 0
    return 0
