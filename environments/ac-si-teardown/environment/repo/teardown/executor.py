"""Run a plan against the cloud and record what happened to every step."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .cloud import Cloud, CloudError
from .planner import Plan, Step


@dataclass
class Outcome:
    step: Step
    status: str      # done | planned | skipped | blocked | failed
    detail: str = ""


def snapshot_volume(cloud: Cloud, step: Step, env: str) -> str:
    """Final snapshot of a volume before deletion (docs/RUNBOOK.md §3)."""
    raise NotImplementedError("snapshot step not implemented yet (docs/RUNBOOK.md §3)")


def execute(plan: Plan, cloud: Cloud, dry_run: bool = False) -> list[Outcome]:
    outcomes: list[Outcome] = []
    not_done: dict[str, str] = {}   # resource id -> why it is still there
    for step in plan.steps:
        if step.action == "skip":
            outcomes.append(Outcome(step, "skipped", step.reason))
            not_done[step.resource_id] = step.reason
            continue
        if step.blocked_by:
            why = f"blocked by out-of-scope {', '.join(step.blocked_by)}"
            outcomes.append(Outcome(step, "blocked", why))
            not_done[step.resource_id] = why
            continue
        pending = [rid for rid in step.after if rid in not_done]
        if pending:
            why = f"waiting on {', '.join(pending)}"
            outcomes.append(Outcome(step, "blocked", why))
            not_done[step.resource_id] = why
            continue
        if dry_run:
            outcomes.append(Outcome(step, "planned", step.reason))
            continue
        try:
            if step.action == "detach":
                cloud.detach(step.resource_id)
                detail = "detached"
            elif step.action == "snapshot":
                detail = snapshot_volume(cloud, step, plan.env)
            elif step.action == "delete":
                cloud.delete(step.resource_id, force=step.force)
                detail = "deleted"
            else:
                raise ValueError(f"unknown action {step.action!r}")
            outcomes.append(Outcome(step, "done", detail))
        except CloudError as exc:
            status = "blocked" if exc.code == "DependencyViolation" else "failed"
            outcomes.append(Outcome(step, status, f"{exc.code}: {exc}"))
            not_done[step.resource_id] = f"{exc.code}: {exc}"
    return outcomes


def today() -> str:
    return date.today().isoformat()
