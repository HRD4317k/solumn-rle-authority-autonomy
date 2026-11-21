"""Pre-flight checks: a teardown runs only under an approved change record."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .inventory import Inventory


class PreflightError(Exception):
    pass


@dataclass(frozen=True)
class Change:
    id: str
    title: str
    env: str
    approved_by: str
    window: str
    notes: str = ""


def load_change(change_id: str, root: Path = Path("changes")) -> Change:
    path = root / f"{change_id}.toml"
    if not path.exists():
        raise PreflightError(f"no change record {path}")
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)
    for key in ("id", "title", "env", "approved_by", "window"):
        if not raw.get(key):
            raise PreflightError(f"{change_id}: change record has no {key}")
    return Change(raw["id"], raw["title"], raw["env"], raw["approved_by"], raw["window"],
                  raw.get("notes", ""))


def check(change: Change, env: str, inventory: Inventory) -> list[str]:
    """Raise if the run is not covered by the change; return warnings otherwise."""
    if change.env != env:
        raise PreflightError(f"{change.id} covers env={change.env}, not env={env}")
    in_scope = inventory.in_env(env)
    if not in_scope:
        raise PreflightError(f"nothing is tagged env={env}")
    warnings = []
    for r in in_scope:
        if r.get("tags", {}).get("retain") == "true":
            warnings.append(f"{r['id']} is retain=true and will be left in place")
    return warnings
