"""python -m grantctl <command>

  reconcile --as-of YYYY-MM-DD [--dry-run]   process the pending queue
  check REQ-ID --as-of YYYY-MM-DD            explain the decision for one request
  grants [--principal P] [--resource R]      list current grants
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from .policy import load_policy
from .reconcile import evaluate, reconcile
from .requests import load_pending
from .state import GrantStore


def cmd_reconcile(args) -> int:
    summary = reconcile(args.root, args.as_of, dry_run=args.dry_run)
    for d in summary.decisions:
        mark = "APPROVED" if d.approved else "REJECTED"
        print(f"{d.request_id:13} {mark:9} {'; '.join(d.reasons)}")
    print(("(dry run) " if args.dry_run else "") + str(summary))
    return 0


def cmd_check(args) -> int:
    policy = load_policy(args.root)
    for req in load_pending(args.root):
        if req.id == args.request_id:
            d = evaluate(req, policy, args.as_of)
            print(f"{req.id}: {d.status} ({', '.join(d.authorities) or 'no authority'})")
            for r in d.reasons:
                print(f"  - {r}")
            return 0 if d.approved else 3
    print(f"{args.request_id}: not in requests/pending/", file=sys.stderr)
    return 1


def cmd_grants(args) -> int:
    store = GrantStore(args.root)
    for g in sorted(store.grants, key=lambda g: (g.resource, g.principal)):
        if args.principal and g.principal != args.principal:
            continue
        if args.resource and g.resource != args.resource:
            continue
        print(f"{g.grant_id}  {g.principal:34} {g.resource:22} {g.level:6} until {g.expires_on}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="grantctl")
    parser.add_argument("--root", type=Path, default=Path("."), help="repository root")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("reconcile")
    p.add_argument("--as-of", type=date.fromisoformat, required=True)
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("check")
    p.add_argument("request_id")
    p.add_argument("--as-of", type=date.fromisoformat, required=True)
    p = sub.add_parser("grants")
    p.add_argument("--principal")
    p.add_argument("--resource")
    args = parser.parse_args(argv)
    args.root = args.root.resolve()
    return {"reconcile": cmd_reconcile, "check": cmd_check, "grants": cmd_grants}[args.command](args)
