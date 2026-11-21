"""A point-in-time view of every resource, with the dependency relation."""
from __future__ import annotations

from dataclasses import dataclass

from .cloud import Cloud


@dataclass
class Inventory:
    resources: dict[str, dict]

    @classmethod
    def from_cloud(cls, cloud: Cloud) -> "Inventory":
        return cls({r["id"]: r for r in cloud.list()})

    @classmethod
    def of(cls, rows: list[dict]) -> "Inventory":
        return cls({r["id"]: r for r in rows})

    def get(self, rid: str) -> dict:
        return self.resources[rid]

    def in_env(self, env: str) -> list[dict]:
        return sorted((r for r in self.resources.values() if r.get("tags", {}).get("env") == env),
                      key=lambda r: r["id"])

    def dependents(self, rid: str) -> list[str]:
        """Resources that reference `rid` and therefore block its deletion
        (the same relation cloudctl enforces)."""
        out = []
        for o in self.resources.values():
            t = o["type"]
            if t in ("subnet", "sg") and o.get("vpc") == rid:
                out.append(o["id"])
            elif t == "instance" and (o.get("subnet") == rid or rid in o.get("sgs", [])):
                out.append(o["id"])
            elif t == "lb" and (rid in o.get("subnets", []) or rid in o.get("targets", [])
                                or rid in o.get("sgs", [])):
                out.append(o["id"])
            elif t == "volume" and o.get("attached_to") == rid:
                out.append(o["id"])
            elif t == "dns" and o.get("target") == rid:
                out.append(o["id"])
        return sorted(out)
