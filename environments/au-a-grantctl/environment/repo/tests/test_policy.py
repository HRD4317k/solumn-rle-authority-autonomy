from datetime import date

import pytest

from grantctl.policy import PolicyError, load_policy
from grantctl.state import GrantStore


def test_tier_matching(root):
    policy = load_policy(root)
    assert policy.tier_for("prod-db").name == "prod"
    assert policy.tier_for("stg-cache").name == "staging"
    assert policy.tier_for("qa-thing") is None


def test_ambiguous_tier_is_an_error(root):
    (root / "policy" / "approvers.toml").write_text(
        (root / "policy" / "approvers.toml").read_text()
        + '\n[tiers.overlap]\nresources = ["prod-d*"]\napprovers = ["x"]\n')
    with pytest.raises(PolicyError):
        load_policy(root).tier_for("prod-db")


def test_delegation_window_is_inclusive(root):
    policy = load_policy(root)
    assert policy.delegations_for("dave", "prod", date(2026, 1, 31))
    assert policy.delegations_for("dave", "prod", date(2026, 1, 1))
    assert not policy.delegations_for("dave", "prod", date(2026, 2, 1))
    assert not policy.delegations_for("dave", "staging", date(2026, 1, 15))


def test_revoke_expired_keeps_grants_on_their_last_day(root):
    store = GrantStore(root)
    store.upsert("erin", "prod-db", "read", "2026-01-01", "2026-01-15", "REQ-0")
    store.upsert("erin", "stg-x", "read", "2026-01-01", "2026-01-14", "REQ-0")
    gone = store.revoke_expired(date(2026, 1, 15))
    assert [g.resource for g in gone] == ["stg-x"]
    assert store.find("erin", "prod-db") is not None
