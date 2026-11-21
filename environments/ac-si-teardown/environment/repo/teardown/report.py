"""Markdown run report (reports/teardown-<env>-<date>.md)."""
from __future__ import annotations

from pathlib import Path

from .executor import Outcome, today

SECTIONS = (("done", "Completed"), ("planned", "Planned (dry run)"), ("skipped", "Skipped"),
            ("blocked", "Blocked - needs follow-up"), ("failed", "Failed"))


def render(env: str, outcomes: list[Outcome], dry_run: bool = False) -> str:
    lines = [f"# Teardown {'plan' if dry_run else 'report'}: {env} ({today()})", ""]
    counts = {}
    for o in outcomes:
        counts[o.status] = counts.get(o.status, 0) + 1
    lines.append("Summary: " + (", ".join(f"{n} {s}" for s, n in sorted(counts.items())) or "nothing to do"))
    for status, title in SECTIONS:
        rows = [o for o in outcomes if o.status == status]
        if not rows:
            continue
        lines += ["", f"## {title}", "", "| step | resource | type | detail |", "|---|---|---|---|"]
        for o in rows:
            lines.append(f"| {o.step.action} | `{o.step.resource_id}` | {o.step.rtype} | {o.detail} |")
    remaining = sorted({o.step.resource_id for o in outcomes if o.status in ("blocked", "failed", "skipped")})
    if remaining and not dry_run:
        lines += ["", "## Still present", ""] + [f"- `{rid}`" for rid in remaining]
    return "\n".join(lines) + "\n"


def write(env: str, outcomes: list[Outcome], out_dir: Path, dry_run: bool = False) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"teardown-{env}-{today()}{'-plan' if dry_run else ''}.md"
    path.write_text(render(env, outcomes, dry_run))
    return path
