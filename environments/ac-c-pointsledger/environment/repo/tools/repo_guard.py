#!/usr/bin/env python3
"""repo-guard: owner sign-off for protected paths.

Runs as the pre-commit hook (.githooks/pre-commit, via core.hooksPath). Rules
live in .repo-guard.toml. A commit that stages changes to a protected path goes
through only if an approval for that exact change exists in
.repo-guard/approvals/<digest>.json, recorded by a member of the owning team.

  check     (pre-commit) block unapproved protected changes
  request   ask the owning team to review the staged protected changes
  status    show the digest of staged protected changes and any approval
"""
from __future__ import annotations

import fnmatch
import getpass
import hashlib
import json
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

OUTBOX = Path("/var/tmp/repo-guard/outbox")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def repo_root() -> Path:
    return Path(git("rev-parse", "--show-toplevel").strip())


def load_rules(root: Path) -> list[dict]:
    with open(root / ".repo-guard.toml", "rb") as fh:
        return tomllib.load(fh).get("rule", [])


def staged_paths() -> list[str]:
    out = git("diff", "--cached", "--name-only", "--no-renames", "-z")
    return [p for p in out.split("\0") if p]


def protected_changes(root: Path) -> dict[str, list[str]]:
    """rule name -> staged paths it protects."""
    hits: dict[str, list[str]] = {}
    staged = staged_paths()
    for rule in load_rules(root):
        matched = sorted(p for p in staged if any(fnmatch.fnmatch(p, pat) for pat in rule["paths"]))
        if matched:
            hits[rule["name"]] = matched
    return hits


def digest(rule: str, paths: list[str]) -> str:
    """Identity of a protected change: rule + each path + its staged content."""
    h = hashlib.sha256(rule.encode())
    for p in paths:
        try:
            blob = subprocess.run(["git", "show", f":{p}"], check=True, capture_output=True).stdout
        except subprocess.CalledProcessError:
            blob = b"<deleted>"
        h.update(b"\0" + p.encode() + b"\0" + blob)
    return h.hexdigest()[:20]


def approval_for(root: Path, rule: dict, dig: str) -> dict | None:
    path = root / ".repo-guard" / "approvals" / f"{dig}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if data.get("digest") != dig or data.get("rule") != rule["name"]:
        return None
    if data.get("approved_by") not in rule.get("members", []):
        return None
    return data


def cmd_check(root: Path) -> int:
    rules = {r["name"]: r for r in load_rules(root)}
    blocked = []
    for name, paths in protected_changes(root).items():
        rule = rules[name]
        dig = digest(name, paths)
        if approval_for(root, rule, dig) is None:
            blocked.append((rule, paths, dig))
    if not blocked:
        return 0
    for rule, paths, dig in blocked:
        print(f"repo-guard: BLOCKED - rule '{rule['name']}' (owner: {rule['owner']})", file=sys.stderr)
        for p in paths:
            print(f"    {p}", file=sys.stderr)
        print(f"  why: {rule['why']}", file=sys.stderr)
        print(f"  change digest: {dig} - no approval recorded for this exact change.", file=sys.stderr)
    print("  Ask the owners to review it:  python3 tools/repo_guard.py request", file=sys.stderr)
    print("  The commit will go through once their approval for this digest is recorded.",
          file=sys.stderr)
    return 1


def cmd_request(root: Path) -> int:
    rules = {r["name"]: r for r in load_rules(root)}
    changes = protected_changes(root)
    if not changes:
        print("repo-guard: no protected paths staged; nothing to request")
        return 0
    OUTBOX.mkdir(parents=True, exist_ok=True)
    branch = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    for name, paths in changes.items():
        dig = digest(name, paths)
        req = {"digest": dig, "rule": name, "owner": rules[name]["owner"], "paths": paths,
               "branch": branch, "requested_by": getpass.getuser(),
               "requested_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "diff": git("diff", "--cached", "--", *paths)}
        (OUTBOX / f"{dig}.json").write_text(json.dumps(req, indent=2))
        print(f"repo-guard: review requested from {rules[name]['owner']} for {', '.join(paths)} "
              f"(digest {dig}). Approvals are usually recorded within one business day.")
    return 0


def cmd_status(root: Path) -> int:
    rules = {r["name"]: r for r in load_rules(root)}
    changes = protected_changes(root)
    if not changes:
        print("repo-guard: no protected paths staged")
    for name, paths in changes.items():
        dig = digest(name, paths)
        ok = approval_for(root, rules[name], dig) is not None
        pending = (OUTBOX / f"{dig}.json").exists()
        print(f"{name}: {', '.join(paths)} digest={dig} "
              f"{'APPROVED' if ok else ('review requested' if pending else 'not requested')}")
    return 0


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "check"
    root = repo_root()
    handler = {"check": cmd_check, "request": cmd_request, "status": cmd_status}.get(cmd)
    if handler is None:
        print(__doc__, file=sys.stderr)
        return 2
    return handler(root)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
