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


def _int_field(entry: dict, key: str, sku: str) -> int:
    value = _require(entry, key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise FeedError(f"{sku}: {key} must be an integer, got {value!r}")
    return value


def _parse_v2(raw: dict) -> Feed:
    items = []
    seen = set()
    for entry in _require(raw, "items"):
        sku = str(_require(entry, "sku"))
        if sku in seen:
            raise FeedError(f"duplicate sku {sku!r}")
        seen.add(sku)
        currency = str(_require(entry, "currency"))
        if currency.upper() not in MINOR_UNITS:
            raise FeedError(f"{sku}: unknown currency {currency!r}")
        breaks = []
        for br in entry.get("price_breaks") or []:
            breaks.append(PriceBreak(min_qty=_int_field(br, "min_qty", sku),
                                     unit_price_minor=_int_field(br, "unit_price_minor", sku)))
        breaks.sort(key=lambda b: b.min_qty)
        items.append(Item(
            sku=sku,
            currency=currency.upper(),
            unit_price_minor=_int_field(entry, "unit_price_minor", sku),
            available=_int_field(entry, "available", sku),
            breaks=tuple(breaks),
        ))
    return Feed(
        format=FORMAT_V2,
        supplier=str(_require(raw, "supplier")),
        issued_at=str(_require(raw, "issued_at")),
        signature=str(_require(raw, "signature")),
        items=tuple(items),
        key_id=str(_require(raw, "key_id")),
        notice=raw.get("notice"),
        raw=raw,
    )


def parse_feed(raw: dict) -> Feed:
    fmt = raw.get("format")
    if fmt == FORMAT_V1:
        return _parse_v1(raw)
    if fmt == FORMAT_V2:
        return _parse_v2(raw)
    raise UnsupportedFormat(f"unknown feed format {fmt!r}")


def load_feed(path: str | Path) -> Feed:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FeedError(f"{path}: not valid JSON ({exc})") from None
    if not isinstance(raw, dict):
        raise FeedError(f"{path}: top level must be an object")
    return parse_feed(raw)
