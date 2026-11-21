"""Access requests: one TOML file per request under requests/pending/.

After reconciliation each request is moved to requests/processed/ with a
[decision] table appended, so the file is the complete record.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

LEVELS = ("read", "write", "admin")


class RequestError(Exception):
    pass


@dataclass(frozen=True)
class AccessRequest:
    id: str
    requester: str
    resource: str
    level: str
    duration_days: int
    approvals: tuple[str, ...]
    ticket: str = ""
    justification: str = ""
    notes: str = ""
    path: Path | None = field(default=None, compare=False)


def parse_request(raw: dict, path: Path | None = None) -> AccessRequest:
    try:
        level = raw["level"]
        if level not in LEVELS:
            raise RequestError(f"{raw.get('id')}: unknown level {level!r}")
        days = int(raw["duration_days"])
        if days <= 0:
            raise RequestError(f"{raw.get('id')}: duration_days must be positive")
        return AccessRequest(
            id=str(raw["id"]),
            requester=str(raw["requester"]),
            resource=str(raw["resource"]),
            level=level,
            duration_days=days,
            approvals=tuple(str(a) for a in raw.get("approvals", [])),
            ticket=str(raw.get("ticket", "")),
            justification=str(raw.get("justification", "")),
            notes=str(raw.get("notes", "")),
            path=path,
        )
    except KeyError as exc:
        raise RequestError(f"{path}: missing field {exc}") from None


def load_pending(root: Path) -> list[AccessRequest]:
    out = []
    for path in sorted((root / "requests" / "pending").glob("*.toml")):
        with open(path, "rb") as fh:
            out.append(parse_request(tomllib.load(fh), path))
    return sorted(out, key=lambda r: r.id)


def _toml_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def archive(request: AccessRequest, root: Path, status: str, decided_on: str,
            reasons: list[str]) -> Path:
    """Append the decision to the request file and move it to processed/."""
    if request.path is None:
        raise RequestError(f"{request.id}: request has no backing file")
    dest_dir = root / "requests" / "processed"
    dest_dir.mkdir(parents=True, exist_ok=True)
    text = request.path.read_text().rstrip("\n")
    text += ("\n\n[decision]\n"
             f"status = {_toml_str(status)}\n"
             f"decided_on = {_toml_str(decided_on)}\n"
             "reasons = [" + ", ".join(_toml_str(r) for r in reasons) + "]\n")
    dest = dest_dir / request.path.name
    dest.write_text(text)
    request.path.unlink()
    return dest
