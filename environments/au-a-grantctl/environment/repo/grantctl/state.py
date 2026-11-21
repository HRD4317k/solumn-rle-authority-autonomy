"""Grant state (state/grants.json) and the append-only audit log (state/audit.jsonl).

state/grants.json is what the nightly IAM sync pushes to the real systems, so
it must only ever contain grants that went through reconciliation.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path


@dataclass
class Grant:
    grant_id: str
    principal: str
    resource: str
    level: str
    granted_on: str
    expires_on: str
    source: str

    def expired_on(self, day: date) -> bool:
        """A grant is valid through its expiry date and lapses the day after."""
        return date.fromisoformat(self.expires_on) < day


class GrantStore:
    def __init__(self, root: Path):
        self.path = root / "state" / "grants.json"
        self.audit_path = root / "state" / "audit.jsonl"
        data = json.loads(self.path.read_text()) if self.path.exists() else {"grants": []}
        self.grants: list[Grant] = [Grant(**g) for g in data["grants"]]

    def _next_id(self) -> str:
        nums = [int(g.grant_id.split("-")[1]) for g in self.grants] or [100]
        return f"G-{max(nums) + 1:04d}"

    def find(self, principal: str, resource: str) -> Grant | None:
        for g in self.grants:
            if g.principal == principal and g.resource == resource:
                return g
        return None

    def upsert(self, principal: str, resource: str, level: str, granted_on: str,
               expires_on: str, source: str) -> tuple[Grant, Grant | None]:
        """Create a grant, replacing any existing grant for the same principal and
        resource. Returns (new_grant, replaced_grant_or_None)."""
        old = self.find(principal, resource)
        if old is not None:
            self.grants.remove(old)
        new = Grant(self._next_id() if old is None else old.grant_id, principal, resource,
                    level, granted_on, expires_on, source)
        self.grants.append(new)
        return new, old

    def revoke_expired(self, day: date) -> list[Grant]:
        gone = [g for g in self.grants if g.expired_on(day)]
        self.grants = [g for g in self.grants if not g.expired_on(day)]
        return gone

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ordered = sorted(self.grants, key=lambda g: g.grant_id)
        self.path.write_text(json.dumps({"grants": [asdict(g) for g in ordered]}, indent=2) + "\n")

    def audit(self, **event) -> None:
        with open(self.audit_path, "a") as fh:
            fh.write(json.dumps(event, sort_keys=True) + "\n")
