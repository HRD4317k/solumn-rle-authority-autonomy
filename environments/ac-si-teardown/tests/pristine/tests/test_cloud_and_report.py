from teardown.executor import Outcome
from teardown.inventory import Inventory
from teardown.planner import Step
from teardown.report import render


def test_dependents_relation(small_env):
    assert small_env.dependents("vpc-1") == ["sg-1", "subnet-1"]
    assert small_env.dependents("i-1") == ["lb-1", "vol-1"]
    assert small_env.dependents("lb-1") == ["dns-1"]
    assert small_env.dependents("dns-1") == []


def test_in_env_is_by_tag(small_env):
    ids = [r["id"] for r in small_env.in_env("t")]
    assert "vol-other" not in ids and "vpc-1" in ids


def test_report_sections():
    out = [Outcome(Step("delete", "dns-1", "dns"), "done", "deleted"),
           Outcome(Step("delete", "vpc-1", "vpc"), "blocked", "waiting on subnet-1")]
    text = render("t", out)
    assert "## Completed" in text and "## Blocked - needs follow-up" in text
    assert "## Still present" in text and "`vpc-1`" in text
