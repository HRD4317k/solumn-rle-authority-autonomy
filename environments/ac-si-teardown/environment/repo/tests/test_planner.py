"""Plan ordering rules (docs/RUNBOOK.md §2-3)."""
from conftest import r

from teardown.inventory import Inventory
from teardown.planner import build_plan


def deletes(plan):
    return [s.resource_id for s in plan.steps if s.action == "delete"]


def test_only_env_resources(small_env):
    plan = build_plan(small_env, "t")
    ids = {s.resource_id for s in plan.steps}
    assert "vol-other" not in ids
    assert "snap-1" not in ids


def test_every_delete_after_its_dependents(small_env):
    plan = build_plan(small_env, "t")
    for rid in deletes(plan):
        for dep in small_env.dependents(rid):
            if dep in deletes(plan):
                assert plan.index("delete", dep) < plan.index("delete", rid), (dep, rid)


def test_volume_detached_snapshotted_then_deleted(small_env):
    plan = build_plan(small_env, "t")
    assert plan.index("detach", "vol-1") < plan.index("delete", "i-1")
    assert plan.index("snapshot", "vol-1") < plan.index("delete", "vol-1")


def test_retained_and_forced_buckets(small_env):
    plan = build_plan(small_env, "t")
    skip = [s for s in plan.steps if s.resource_id == "bucket-keep"]
    assert [s.action for s in skip] == ["skip"]
    b1 = next(s for s in plan.steps if s.resource_id == "bucket-1")
    assert b1.action == "delete" and b1.force


def test_foreign_reference_blocks(small_env):
    inv = Inventory.of(list(small_env.resources.values()) + [
        r("i-x", "instance", env="someone-else", subnet="subnet-1", sgs=[])])
    plan = build_plan(inv, "t")
    sub = plan.steps[plan.index("delete", "subnet-1")]
    assert sub.blocked_by == ("i-x",)
    vpc = plan.steps[plan.index("delete", "vpc-1")]
    assert "subnet-1" in vpc.after
