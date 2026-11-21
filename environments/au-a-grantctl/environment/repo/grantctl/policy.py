"""Access policy: who may approve what, and standing delegations.

policy/approvers.toml   one table per tier: resource patterns, approvers,
                        how many distinct approvers an admin grant needs,
                        and the maximum grant length.
policy/delegations.toml time-boxed delegations of an approver's authority.
"""
from __future__ import annotations

import fnmatch
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class Tier:
    name: str
    resources: tuple[str, ...]
    approvers: frozenset[str]
    admin_requires: int
    max_days: int

    def covers(self, resource: str) -> bool:
        return any(fnmatch.fnmatchcase(resource, pat) for pat in self.resources)


@dataclass(frozen=True)
class Delegation:
    delegator: str
    delegate: str
    tiers: frozenset[str]
    starts: date
    expires: date
    reason: str = ""

    def active_on(self, day: date) -> bool:
        """Delegations are inclusive of both their start and expiry dates."""
        return self.starts <= day <= self.expires


class PolicyError(Exception):
    pass


@dataclass(frozen=True)
class Policy:
    tiers: tuple[Tier, ...]
    delegations: tuple[Delegation, ...]

    def tier_for(self, resource: str) -> Tier | None:
        matches = [t for t in self.tiers if t.covers(resource)]
        if len(matches) > 1:
            names = ", ".join(t.name for t in matches)
            raise PolicyError(f"resource {resource!r} matches more than one tier ({names})")
        return matches[0] if matches else None

    def delegations_for(self, delegate: str, tier: str, day: date) -> list[Delegation]:
        return [d for d in self.delegations
                if d.delegate == delegate and tier in d.tiers and d.active_on(day)]


def _date(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def load_policy(root: Path) -> Policy:
    with open(root / "policy" / "approvers.toml", "rb") as fh:
        raw = tomllib.load(fh)
    tiers = []
    for name, t in raw.get("tiers", {}).items():
        tiers.append(Tier(
            name=name,
            resources=tuple(t["resources"]),
            approvers=frozenset(t["approvers"]),
            admin_requires=int(t.get("admin_requires", 1)),
            max_days=int(t.get("max_days", 90)),
        ))
    delegations = []
    dpath = root / "policy" / "delegations.toml"
    if dpath.exists():
        with open(dpath, "rb") as fh:
            draw = tomllib.load(fh)
        for d in draw.get("delegation", []):
            delegations.append(Delegation(
                delegator=d["from"], delegate=d["to"], tiers=frozenset(d["tiers"]),
                starts=_date(d["starts"]), expires=_date(d["expires"]),
                reason=d.get("reason", "")))
    return Policy(tuple(tiers), tuple(delegations))
