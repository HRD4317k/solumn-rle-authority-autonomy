"""python -m loyalty [--db PATH] <command>

  migrate                                  apply pending migrations
  enroll ID NAME --at TS
  earn ID POINTS --at TS [--ref R]
  purchase ID AMOUNT_MINOR --at TS [--ref R]
  redeem ID POINTS --at TS [--ref R]
  balance ID [--at TS]
  statement ID YYYY-MM [--json]
"""
from __future__ import annotations

import argparse
import json
import sys

from . import members
from .db import connect, migrate
from .ledger import Ledger, LedgerError
from .statements import render, statement


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="loyalty")
    p.add_argument("--db", default="var/loyalty.db")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate")
    for name in ("enroll", "earn", "purchase", "redeem"):
        sp = sub.add_parser(name)
        sp.add_argument("member")
        sp.add_argument("value")
        sp.add_argument("--at", required=True)
        sp.add_argument("--ref")
    sp = sub.add_parser("balance")
    sp.add_argument("member")
    sp.add_argument("--at")
    sp = sub.add_parser("statement")
    sp.add_argument("member")
    sp.add_argument("period")
    sp.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    conn = connect(args.db)
    try:
        if args.cmd == "migrate":
            for name in migrate(conn):
                print(f"applied {name}")
        elif args.cmd == "enroll":
            members.enroll(conn, args.member, args.value, args.at)
        elif args.cmd == "earn":
            Ledger(conn).earn(args.member, int(args.value), args.at, args.ref)
        elif args.cmd == "purchase":
            pts = members.award_purchase(conn, args.member, int(args.value), args.at, args.ref)
            print(f"awarded {pts} points")
        elif args.cmd == "redeem":
            Ledger(conn).redeem(args.member, int(args.value), args.at, args.ref)
        elif args.cmd == "balance":
            print(Ledger(conn).balance(args.member, args.at))
        elif args.cmd == "statement":
            year, month = (int(x) for x in args.period.split("-"))
            stmt = statement(conn, args.member, year, month)
            print(json.dumps(stmt, indent=2) if args.json else render(stmt))
    except LedgerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        conn.close()
    return 0
