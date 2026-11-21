"""Turn an environment's inventory into an ordered teardown plan.

See docs/RUNBOOK.md for the rules the plan has to follow.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .inventory import Inventory

ACTIONS = ("detach", "snapshot", "delete", "skip")


@dataclass(frozen=True)
class Step:
    action: str            # one of ACTIONS
    resource_id: str
    rtype: str
    reason: str = ""
    force: bool = False    # delete --force (non-empty buckets)
    after: tuple[str, ...] = ()       # resource ids whose steps must have succeeded first
    blocked_by: tuple[str, ...] = ()  # out-of-scope resources that prevent this step


@dataclass
class Plan:
    env: str
    steps: list[Step] = field(default_factory=list)

    def index(self, action: str, rid: str) -> int:
        for i, s in enumerate(self.steps):
            if s.action == action and s.resource_id == rid:
                return i
        raise KeyError((action, rid))


def build_plan(inventory: Inventory, env: str) -> Plan:
    """Ordered steps that remove every resource tagged env=<env>."""
    raise NotImplementedError("dependency ordering not implemented yet (docs/RUNBOOK.md §2)")
