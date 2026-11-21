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
    scope = {r["id"]: r for r in inventory.in_env(env) if r["type"] != "snapshot"}
    plan = Plan(env)
    retained = {rid for rid, r in scope.items() if r.get("tags", {}).get("retain") == "true"}
    for rid in sorted(retained):
        plan.steps.append(Step("skip", rid, scope[rid]["type"], "retain=true (legal hold)"))
    live = {rid: r for rid, r in scope.items() if rid not in retained}

    # Edges: a resource can be deleted once every resource referencing it is gone.
    # Attached volumes are detached first, so they do not block their instance.
    deps: dict[str, set[str]] = {}
    foreign: dict[str, set[str]] = {}
    for rid in live:
        deps[rid] = set()
        foreign[rid] = set()
        for d in inventory.dependents(rid):
            dep = inventory.get(d)
            if dep["type"] == "snapshot":
                continue
            if dep["type"] == "volume" and dep.get("attached_to") == rid and d in live:
                continue
            if d in live:
                deps[rid].add(d)
            else:  # out of scope, or retained in scope: this run cannot remove it
                foreign[rid].add(d)

    # detach / snapshot steps up front
    for rid in sorted(live):
        r = live[rid]
        if r["type"] == "volume" and r.get("attached_to"):
            plan.steps.append(Step("detach", rid, "volume", f"detach from {r['attached_to']}"))
        if r["type"] == "volume" and r.get("tags", {}).get("backup") == "required":
            plan.steps.append(Step("snapshot", rid, "volume", "final snapshot (backup=required)"))

    # topological order (Kahn), stable by id
    blocked_transitively: dict[str, set[str]] = {rid: set(foreign[rid]) for rid in live}
    remaining = dict(deps)
    done: list[str] = []
    while remaining:
        ready = sorted(rid for rid, ds in remaining.items() if not (ds - set(done)))
        if not ready:
            raise ValueError(f"dependency cycle among {sorted(remaining)}")
        for rid in ready:
            done.append(rid)
            del remaining[rid]
    for rid in done:
        r = live[rid]
        after = sorted(deps[rid])
        plan.steps.append(Step(
            "delete", rid, r["type"],
            reason=f"after {', '.join(after)}" if after else "",
            force=r["type"] == "bucket",
            after=tuple(after),
            blocked_by=tuple(sorted(blocked_transitively[rid]))))
    return plan
