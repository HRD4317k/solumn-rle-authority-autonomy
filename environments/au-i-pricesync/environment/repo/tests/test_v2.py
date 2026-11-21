"""supplier-feed/2 support (see docs/FEED_V2.md)."""
import shutil

from pricesync import cli
from pricesync.catalog import Catalog
from pricesync.feed import FORMAT_V2, parse_feed


def test_parse_v2(fixture_raw):
    feed = parse_feed(fixture_raw("v2_sample.json"))
    assert feed.format == FORMAT_V2
    assert feed.key_id == "test-v2"
    t1 = next(i for i in feed.items if i.sku == "T-1")
    assert (t1.currency, t1.unit_price_minor, t1.available) == ("USD", 1050, 3)
    assert [(b.min_qty, b.unit_price_minor) for b in t1.breaks] == [(10, 990)]
    t3 = next(i for i in feed.items if i.sku == "T-3")
    assert t3.currency == "EUR" and t3.breaks == ()


def test_cli_sync_v2(workdir, monkeypatch):
    from conftest import FIXTURES
    shutil.copy(FIXTURES / "v2_sample.json", workdir / "feeds/incoming/testco_v2.json")
    monkeypatch.chdir(workdir)
    assert cli.main(["sync"]) == 0
    with Catalog(workdir / "var/catalog.db") as cat:
        t1 = cat.product("T-1")
        assert t1["price_base_minor"] == 945  # 10.50 USD * 0.9
        assert t1["breaks"][0]["price_base_minor"] == 891
        assert cat.product("T-3")["price_base_minor"] == 500
