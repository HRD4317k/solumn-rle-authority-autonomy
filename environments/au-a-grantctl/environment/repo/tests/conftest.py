from datetime import date
from pathlib import Path

import pytest

from grantctl.requests import parse_request

APPROVERS = """
[tiers.prod]
resources = ["prod-*"]
approvers = ["alice", "bob"]
admin_requires = 2
max_days = 90

[tiers.staging]
resources = ["stg-*"]
approvers = ["alice", "carol"]
admin_requires = 1
max_days = 180
"""

DELEGATIONS = """
[[delegation]]
from = "alice"
to = "dave"
tiers = ["prod"]
starts = 2026-01-01
expires = 2026-01-31
"""


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "policy").mkdir()
    (tmp_path / "policy" / "approvers.toml").write_text(APPROVERS)
    (tmp_path / "policy" / "delegations.toml").write_text(DELEGATIONS)
    (tmp_path / "requests" / "pending").mkdir(parents=True)
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "grants.json").write_text('{"grants": []}\n')
    return tmp_path


@pytest.fixture
def make_request():
    def make(**kw):
        base = dict(id="REQ-1", requester="erin", resource="prod-db", level="read",
                    duration_days=10, approvals=["alice"])
        base.update(kw)
        return parse_request(base)
    return make


JAN15 = date(2026, 1, 15)
