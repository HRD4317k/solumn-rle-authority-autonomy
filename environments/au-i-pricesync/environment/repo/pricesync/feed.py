"""Supplier feed parsing.

A feed is a JSON document describing a supplier's full price list at a point
in time. Parsing turns it into a `Feed` with integer minor-unit prices; the
original decoded JSON is kept on `Feed.raw` because signatures are computed
over transmitted values, not over our normalised ones.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

FORMAT_V1 = "supplier-feed/1"
FORMAT_V2 = "supplier-feed/2"

# ISO 4217 minor-unit exponents for the currencies our suppliers use.
MINOR_UNITS = {"EUR": 2, "USD": 2, "GBP": 2, "CHF": 2, "SEK": 2, "JPY": 0}


class FeedError(Exception):
    """The feed is malformed."""


class UnsupportedFormat(FeedError):
    """The feed declares a format this version of pricesync cannot read."""


@dataclass(frozen=True)
class PriceBreak:
    min_qty: int
    unit_price_minor: int


@dataclass(frozen=True)
class Item:
    sku: str
    currency: str
    unit_price_minor: int
    available: int
    breaks: tuple[PriceBreak, ...] = ()


@dataclass(frozen=True)
class Feed:
    format: str
    supplier: str
    issued_at: str
    signature: str
    items: tuple[Item, ...]
    key_id: str | None = None
    notice: str | None = None
    raw: dict = field(default_factory=dict, compare=False, repr=False)


def to_minor(amount: str, currency: str) -> int:
    """Convert a decimal string like "12.50" to integer minor units."""
    exp = MINOR_UNITS.get(currency.upper())
    if exp is None:
        raise FeedError(f"unknown currency {currency!r}")
    try:
        value = Decimal(str(amount))
    except InvalidOperation:
        raise FeedError(f"bad amount {amount!r}") from None
    scaled = value.scaleb(exp)
    if scaled != scaled.to_integral_value():
        raise FeedError(f"amount {amount!r} has more precision than {currency} allows")
    return int(scaled)


def _require(raw: dict, key: str):
    if key not in raw:
        raise FeedError(f"feed is missing required field {key!r}")
    return raw[key]


def _parse_v1(raw: dict) -> Feed:
    currency = str(_require(raw, "currency")).upper()
    items = []
    seen = set()
    for entry in _require(raw, "items"):
        sku = str(_require(entry, "sku"))
        if sku in seen:
            raise FeedError(f"duplicate sku {sku!r}")
        seen.add(sku)
        items.append(Item(
            sku=sku,
            currency=currency,
            unit_price_minor=to_minor(_require(entry, "price"), currency),
            available=int(entry.get("stock", 0)),
        ))
    return Feed(
        format=FORMAT_V1,
        supplier=str(_require(raw, "supplier")),
        issued_at=str(_require(raw, "generated")),
        signature=str(_require(raw, "signature")),
        items=tuple(items),
        notice=raw.get("notice"),
        raw=raw,
    )


def parse_feed(raw: dict) -> Feed:
    fmt = raw.get("format")
    if fmt == FORMAT_V1:
        return _parse_v1(raw)
    if fmt == FORMAT_V2:
        raise UnsupportedFormat(f"feed format {fmt!r} is not supported yet")
    raise UnsupportedFormat(f"unknown feed format {fmt!r}")


def load_feed(path: str | Path) -> Feed:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FeedError(f"{path}: not valid JSON ({exc})") from None
    if not isinstance(raw, dict):
        raise FeedError(f"{path}: top level must be an object")
    return parse_feed(raw)
