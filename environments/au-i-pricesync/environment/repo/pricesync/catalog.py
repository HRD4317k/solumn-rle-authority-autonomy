"""SQLite-backed product catalog.

Prices are stored twice: in the supplier's currency (minor units, exactly as
the feed sent them) and converted to the catalog's base currency (minor units,
banker's rounding) for the storefront.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path

from .feed import MINOR_UNITS, Feed

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    sku               TEXT PRIMARY KEY,
    supplier          TEXT NOT NULL,
    currency          TEXT NOT NULL,
    unit_price_minor  INTEGER NOT NULL,
    price_base_minor  INTEGER NOT NULL,
    available         INTEGER NOT NULL,
    feed_issued_at    TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS price_breaks (
    sku               TEXT NOT NULL,
    min_qty           INTEGER NOT NULL,
    unit_price_minor  INTEGER NOT NULL,
    price_base_minor  INTEGER NOT NULL,
    PRIMARY KEY (sku, min_qty)
);
CREATE TABLE IF NOT EXISTS price_history (
    sku               TEXT NOT NULL,
    old_base_minor    INTEGER,
    new_base_minor    INTEGER NOT NULL,
    changed_at        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sync_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_name TEXT NOT NULL,
    supplier  TEXT,
    format    TEXT,
    items     INTEGER,
    status    TEXT NOT NULL,
    detail    TEXT,
    at        TEXT NOT NULL
);
"""


@dataclass
class ApplyStats:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    stale: int = 0
    delisted: int = 0

    def __str__(self) -> str:
        return (f"{self.inserted} new, {self.updated} updated, {self.unchanged} unchanged, "
                f"{self.stale} stale, {self.delisted} delisted")


def convert_minor(amount_minor: int, currency: str, base: str, rate: Decimal) -> int:
    """Convert minor units of `currency` to minor units of `base`."""
    src_exp = MINOR_UNITS[currency.upper()]
    dst_exp = MINOR_UNITS[base.upper()]
    major = Decimal(amount_minor).scaleb(-src_exp)
    converted = (major * rate).scaleb(dst_exp)
    return int(converted.quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


class Catalog:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if exc[0] is None:
            self.conn.commit()
        self.close()

    def product(self, sku: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM products WHERE sku = ?", (sku,)).fetchone()
        if row is None:
            return None
        out = dict(row)
        out["breaks"] = [dict(r) for r in self.conn.execute(
            "SELECT min_qty, unit_price_minor, price_base_minor FROM price_breaks "
            "WHERE sku = ? ORDER BY min_qty", (sku,))]
        return out

    def apply_feed(self, feed: Feed, base: str, rates: dict[str, Decimal], now: str) -> ApplyStats:
        """Upsert every item of a (verified) feed. A feed is a full price list:
        SKUs of this supplier that are missing from it are marked unavailable.
        Items whose stored version came from a newer feed are left alone."""
        stats = ApplyStats()
        cur = self.conn.cursor()
        seen = set()
        for item in feed.items:
            seen.add(item.sku)
            rate = rates[item.currency.upper()]
            base_minor = convert_minor(item.unit_price_minor, item.currency, base, rate)
            existing = cur.execute(
                "SELECT price_base_minor, feed_issued_at, unit_price_minor, available "
                "FROM products WHERE sku = ?", (item.sku,)).fetchone()
            if existing is not None and existing["feed_issued_at"] > feed.issued_at:
                stats.stale += 1
                continue
            if existing is None:
                stats.inserted += 1
                cur.execute("INSERT INTO price_history VALUES (?, NULL, ?, ?)",
                            (item.sku, base_minor, now))
            elif (existing["unit_price_minor"], existing["available"]) != (
                    item.unit_price_minor, item.available) or existing["price_base_minor"] != base_minor:
                stats.updated += 1
                if existing["price_base_minor"] != base_minor:
                    cur.execute("INSERT INTO price_history VALUES (?, ?, ?, ?)",
                                (item.sku, existing["price_base_minor"], base_minor, now))
            else:
                stats.unchanged += 1
            cur.execute(
                "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(sku) DO UPDATE SET supplier=excluded.supplier, "
                "currency=excluded.currency, unit_price_minor=excluded.unit_price_minor, "
                "price_base_minor=excluded.price_base_minor, available=excluded.available, "
                "feed_issued_at=excluded.feed_issued_at, updated_at=excluded.updated_at",
                (item.sku, feed.supplier, item.currency.upper(), item.unit_price_minor,
                 base_minor, item.available, feed.issued_at, now))
            cur.execute("DELETE FROM price_breaks WHERE sku = ?", (item.sku,))
            for br in item.breaks:
                cur.execute("INSERT INTO price_breaks VALUES (?, ?, ?, ?)", (
                    item.sku, br.min_qty, br.unit_price_minor,
                    convert_minor(br.unit_price_minor, item.currency, base, rate)))
        for row in cur.execute(
                "SELECT sku FROM products WHERE supplier = ? AND available > 0 "
                "AND feed_issued_at < ?", (feed.supplier, feed.issued_at)).fetchall():
            if row["sku"] not in seen:
                cur.execute("UPDATE products SET available = 0, updated_at = ? WHERE sku = ?",
                            (now, row["sku"]))
                stats.delisted += 1
        self.conn.commit()
        return stats

    def log_sync(self, feed_name: str, status: str, now: str, feed: Feed | None = None,
                 detail: str = "") -> None:
        self.conn.execute(
            "INSERT INTO sync_log (feed_name, supplier, format, items, status, detail, at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (feed_name, feed.supplier if feed else None, feed.format if feed else None,
             len(feed.items) if feed else None, status, detail, now))
        self.conn.commit()

    def recent_log(self, limit: int = 20) -> list[dict]:
        return [dict(r) for r in self.conn.execute(
            "SELECT * FROM sync_log ORDER BY id DESC LIMIT ?", (limit,))]
