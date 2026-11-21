#!/usr/bin/env python3
"""cloudctl - CLI for the Crestline private cloud (offline sandbox endpoint).

State: $CLOUDSIM_STATE (default /var/tmp/cloudsim/state.json). Every mutating
call is recorded in audit.jsonl next to the state file.

  cloudctl list [--type T] [--tag K=V ...] [--json]
  cloudctl describe ID [--json]
  cloudctl delete ID [--force]        (--force empties a bucket first)
  cloudctl detach VOLUME_ID
  cloudctl snapshot VOLUME_ID [--note TEXT]
  cloudctl tag ID K=V [K=V ...]
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE = Path(os.environ.get("CLOUDSIM_STATE", "/var/tmp/cloudsim/state.json"))
AUDIT = STATE.with_name("audit.jsonl")
EXIT_ERR = 3


class CloudError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load() -> dict:
    return json.loads(STATE.read_text())


def save(state: dict) -> None:
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True))
    tmp.replace(STATE)


def audit(cmd: str, target: str | None, ok: bool, detail: str = "", **extra) -> None:
    with open(AUDIT, "a") as fh:
        fh.write(json.dumps({"ts": now(), "cmd": cmd, "target": target,
                             "result": "ok" if ok else "error", "detail": detail, **extra},
                            sort_keys=True) + "\n")


def get(state: dict, rid: str) -> dict:
    try:
        return state["resources"][rid]
    except KeyError:
        raise CloudError("NotFound", f"resource {rid} does not exist") from None


def dependents(state: dict, rid: str) -> list[str]:
    """Resources that must be removed (or detached) before `rid` can be deleted."""
    out = []
    for other in state["resources"].values():
        t = other["type"]
        if t in ("subnet", "sg") and other.get("vpc") == rid:
            out.append(other["id"])
        elif t == "instance" and (other.get("subnet") == rid or rid in other.get("sgs", [])):
            out.append(other["id"])
        elif t == "lb" and (rid in other.get("subnets", []) or rid in other.get("targets", [])
                            or rid in other.get("sgs", [])):
            out.append(other["id"])
        elif t == "volume" and other.get("attached_to") == rid:
            out.append(other["id"])
        elif t == "dns" and other.get("target") == rid:
            out.append(other["id"])
    return sorted(out)


def do_delete(state: dict, rid: str, force: bool) -> str:
    res = get(state, rid)
    if res.get("tags", {}).get("retain") == "true":
        raise CloudError("DeletionProtected", f"{rid} is tagged retain=true")
    if res["type"] == "snapshot":
        raise CloudError("OperationNotPermitted", "snapshots are deleted by the backup lifecycle")
    if res["type"] == "volume" and res.get("attached_to"):
        raise CloudError("VolumeInUse", f"{rid} is attached to {res['attached_to']}")
    if res["type"] == "bucket" and res.get("objects", 0) and not force:
        raise CloudError("BucketNotEmpty", f"{rid} holds {res['objects']} objects (use --force)")
    deps = dependents(state, rid)
    if deps:
        raise CloudError("DependencyViolation", f"{rid} has dependent resources: {', '.join(deps)}")
    del state["resources"][rid]
    return f"deleted {rid}"


def do_snapshot(state: dict, vid: str, note: str) -> str:
    vol = get(state, vid)
    if vol["type"] != "volume":
        raise CloudError("InvalidParameter", f"{vid} is not a volume")
    state["seq"] = state.get("seq", 0) + 1
    sid = f"snap-{state['seq']:05d}"
    state["resources"][sid] = {"id": sid, "type": "snapshot", "name": f"{vol['name']}-final",
                               "volume": vid, "size_gb": vol.get("size_gb"), "note": note,
                               "created": now(), "tags": dict(vol.get("tags", {}))}
    return sid


def matches(res: dict, rtype: str | None, tags: list[str]) -> bool:
    if rtype and res["type"] != rtype:
        return False
    for kv in tags:
        k, _, v = kv.partition("=")
        if res.get("tags", {}).get(k) != v:
            return False
    return True


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="cloudctl")
    sub = p.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("list")
    sp.add_argument("--type")
    sp.add_argument("--tag", action="append", default=[])
    sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("describe")
    sp.add_argument("id")
    sp.add_argument("--json", action="store_true")
    sp = sub.add_parser("delete")
    sp.add_argument("id")
    sp.add_argument("--force", action="store_true")
    sp = sub.add_parser("detach")
    sp.add_argument("id")
    sp = sub.add_parser("snapshot")
    sp.add_argument("id")
    sp.add_argument("--note", default="")
    sp = sub.add_parser("tag")
    sp.add_argument("id")
    sp.add_argument("pairs", nargs="+")
    a = p.parse_args(argv)

    lock = open(STATE.with_suffix(".lock"), "w")
    fcntl.flock(lock, fcntl.LOCK_EX)
    state = load()
    try:
        if a.cmd == "list":
            rows = [r for r in state["resources"].values() if matches(r, a.type, a.tag)]
            rows.sort(key=lambda r: (r["type"], r["id"]))
            if a.json:
                print(json.dumps(rows, indent=2))
            else:
                for r in rows:
                    tags = ",".join(f"{k}={v}" for k, v in sorted(r.get("tags", {}).items()))
                    print(f"{r['id']:26} {r['type']:9} {r.get('name', ''):30} {tags}")
            return 0
        if a.cmd == "describe":
            res = dict(get(state, a.id))
            res["dependents"] = dependents(state, a.id)
            print(json.dumps(res, indent=2))
            return 0
        if a.cmd == "delete":
            msg = do_delete(state, a.id, a.force)
        elif a.cmd == "detach":
            vol = get(state, a.id)
            if vol["type"] != "volume" or not vol.get("attached_to"):
                raise CloudError("InvalidParameter", f"{a.id} is not an attached volume")
            msg = f"detached {a.id} from {vol['attached_to']}"
            vol["attached_to"] = None
        elif a.cmd == "snapshot":
            msg = do_snapshot(state, a.id, a.note)
        else:  # tag
            res = get(state, a.id)
            for kv in a.pairs:
                k, _, v = kv.partition("=")
                res.setdefault("tags", {})[k] = v
            msg = f"tagged {a.id}"
        save(state)
        audit(a.cmd, a.id, True, msg, args=sys.argv[2:] if argv is None else list(argv)[1:])
        print(msg)
        return 0
    except CloudError as exc:
        if a.cmd not in ("list", "describe"):
            audit(a.cmd, getattr(a, "id", None), False, f"{exc.code}: {exc}")
        print(f"error: {exc.code}: {exc}", file=sys.stderr)
        return EXIT_ERR
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)


if __name__ == "__main__":
    sys.exit(main())
