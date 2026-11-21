import json
import shutil

import pytest

from pricesync import cli
from pricesync.catalog import Catalog, convert_minor
from pricesync.feed import FeedError, parse_feed, to_minor
from pricesync.signing import SignatureError, verify_feed
from decimal import Decimal


def test_to_minor():
    assert to_minor("12.50", "USD") == 1250
    assert to_minor("7", "JPY") == 7
    with pytest.raises(FeedError):
        to_minor("1.005", "USD")


def test_convert_minor_bankers_rounding():
    # 0.25 USD * 0.9 = 0.225 EUR -> 0.22 (half-even)
    assert convert_minor(25, "USD", "EUR", Decimal("0.9")) == 22
    assert convert_minor(35, "USD", "EUR", Decimal("0.9")) == 32  # 0.315 -> 0.32


def test_parse_v1(fixture_raw):
    feed = parse_feed(fixture_raw("v1_sample.json"))
    assert feed.supplier == "testco"
    assert [(i.sku, i.unit_price_minor, i.available) for i in feed.items] == [
        ("T-1", 1000, 5), ("T-2", 99, 0)]


def test_verify_v1(fixture_raw, test_keyring):
    raw = fixture_raw("v1_sample.json")
    assert verify_feed(parse_feed(raw), test_keyring).key_id == "test-v1"
    raw["items"][0]["price"] = "1.00"
    with pytest.raises(SignatureError):
        verify_feed(parse_feed(raw), test_keyring)


def test_cli_sync_v1(workdir, monkeypatch):
    from conftest import FIXTURES
    shutil.copy(FIXTURES / "v1_sample.json", workdir / "feeds/incoming/testco.json")
    monkeypatch.chdir(workdir)
    assert cli.main(["sync"]) == 0
    assert (workdir / "feeds/archive/testco.json").exists()
    with Catalog(workdir / "var/catalog.db") as cat:
        assert cat.product("T-1")["price_base_minor"] == 900


def test_cli_quarantines_bad_signature(workdir, monkeypatch):
    from conftest import FIXTURES
    raw = json.loads((FIXTURES / "v1_sample.json").read_text())
    raw["items"][1]["stock"] = 999
    (workdir / "feeds/incoming/bad.json").write_text(json.dumps(raw))
    monkeypatch.chdir(workdir)
    assert cli.main(["sync"]) == 2
    assert (workdir / "quarantine/bad.json").exists()
    with Catalog(workdir / "var/catalog.db") as cat:
        assert cat.product("T-2") is None
