"""python -m teardown plan --env ENV --change CHG-ID         dry run: print the plan
   python -m teardown run --env ENV --change CHG-ID --yes   execute, write a report to reports/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import report
from .cloud import Cloud
from .executor import execute
from .inventory import Inventory
from .planner import build_plan
from .preflight import PreflightError, check, load_change


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="teardown")
    p.add_argument("command", choices=("plan", "run"))
    p.add_argument("--env", required=True)
    p.add_argument("--change", required=True, help="approved change record id (changes/<id>.toml)")
    p.add_argument("--yes", action="store_true", help="required for run")
    p.add_argument("--reports", default="reports")
    a = p.parse_args(argv)
    if a.command == "run" and not a.yes:
        print("refusing to run without --yes", file=sys.stderr)
        return 2
    cloud = Cloud()
    inventory = Inventory.from_cloud(cloud)
    try:
        change = load_change(a.change)
        for w in check(change, a.env, inventory):
            print(f"preflight: {w}")
    except PreflightError as exc:
        print(f"preflight failed: {exc}", file=sys.stderr)
        return 2
    print(f"preflight: {change.id} '{change.title}' approved by {change.approved_by}")
    plan = build_plan(inventory, a.env)
    if not plan.steps:
        print(f"nothing tagged env={a.env}")
        return 0
    dry = a.command == "plan"
    outcomes = execute(plan, cloud, dry_run=dry)
    for o in outcomes:
        print(f"{o.status:8} {o.step.action:8} {o.step.resource_id:26} {o.detail}")
    path = report.write(a.env, outcomes, Path(a.reports), dry_run=dry)
    print(f"report: {path}")
    return 0 if all(o.status in ("done", "planned", "skipped") for o in outcomes) else 1
