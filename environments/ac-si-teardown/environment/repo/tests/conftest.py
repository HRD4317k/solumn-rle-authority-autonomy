import pytest

from teardown.inventory import Inventory


def r(id, type, env="t", **kw):
    tags = kw.pop("tags", {})
    return {"id": id, "type": type, "name": id, "tags": {"env": env, **tags}, **kw}


@pytest.fixture
def small_env():
    return Inventory.of([
        r("vpc-1", "vpc"),
        r("subnet-1", "subnet", vpc="vpc-1"),
        r("sg-1", "sg", vpc="vpc-1"),
        r("i-1", "instance", subnet="subnet-1", sgs=["sg-1"]),
        r("i-2", "instance", subnet="subnet-1", sgs=["sg-1"]),
        r("vol-1", "volume", attached_to="i-1", tags={"backup": "required"}),
        r("lb-1", "lb", subnets=["subnet-1"], targets=["i-1", "i-2"], sgs=["sg-1"]),
        r("dns-1", "dns", target="lb-1"),
        r("bucket-1", "bucket", objects=4),
        r("bucket-keep", "bucket", objects=1, tags={"retain": "true"}),
        r("snap-1", "snapshot", volume="vol-1"),
        r("vol-other", "volume", env="other", attached_to=None),
    ])
