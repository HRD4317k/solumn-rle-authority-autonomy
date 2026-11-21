import json

from conftest import JAN15

from grantctl.policy import load_policy
from grantctl.reconcile import evaluate, reconcile


def test_single_approver(root, make_request):
    d = evaluate(make_request(), load_policy(root), JAN15)
    assert d.approved and d.authorities == ["alice"] and d.days == 10


def test_self_approval_does_not_count(root, make_request):
    d = evaluate(make_request(requester="alice", approvals=["alice"]), load_policy(root), JAN15)
    assert not d.approved and d.reasons


def test_delegate_counts_as_delegator(root, make_request):
    d = evaluate(make_request(approvals=["dave"]), load_policy(root), JAN15)
    assert d.approved and d.authorities == ["alice"]


def test_admin_needs_distinct_authorities(root, make_request):
    policy = load_policy(root)
    d = evaluate(make_request(level="admin", approvals=["alice", "dave"]), policy, JAN15)
    assert not d.approved  # dave acts for alice: one authority
    d = evaluate(make_request(level="admin", approvals=["bob", "dave"]), policy, JAN15)
    assert d.approved and sorted(d.authorities) == ["alice", "bob"]


def test_duration_is_clamped(root, make_request):
    d = evaluate(make_request(duration_days=400), load_policy(root), JAN15)
    assert d.approved and d.days == 90


def test_unknown_resource_rejected(root, make_request):
    d = evaluate(make_request(resource="qa-db"), load_policy(root), JAN15)
    assert not d.approved


def test_reconcile_end_to_end(root):
    (root / "requests/pending/REQ-1.toml").write_text(
        'id = "REQ-1"\nrequester = "erin"\nresource = "stg-cache"\nlevel = "write"\n'
        'duration_days = 30\napprovals = ["carol"]\n')
    (root / "requests/pending/REQ-2.toml").write_text(
        'id = "REQ-2"\nrequester = "frank"\nresource = "prod-db"\nlevel = "write"\n'
        'duration_days = 30\napprovals = ["zed"]\n')
    summary = reconcile(root, JAN15)
    assert (summary.approved, summary.rejected) == (1, 1)
    grants = json.loads((root / "state/grants.json").read_text())["grants"]
    assert [(g["principal"], g["resource"], g["expires_on"]) for g in grants] == [
        ("erin", "stg-cache", "2026-02-14")]
    assert not list((root / "requests/pending").iterdir())
    assert len(list((root / "requests/processed").iterdir())) == 2
