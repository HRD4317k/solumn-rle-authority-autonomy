"""Configuration loading for pricesync.

The config file is TOML (config/pricesync.toml by default, override with the
PRICESYNC_CONFIG environment variable). Relative paths inside it are resolved
against the project root, so the tool can be run from anywhere.
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

DEFAULT_CONFIG = Path("config/pricesync.toml")


@dataclass(frozen=True)
class SignaturePolicy:
    enforce: bool
    keyring: Path


@dataclass(frozen=True)
class Config:
    root: Path
    db_path: Path
    base_currency: str
    incoming: Path
    archive: Path
    quarantine: Path
    signature: SignaturePolicy
    rates: dict[str, Decimal]

    def rate(self, currency: str) -> Decimal:
        try:
            return self.rates[currency.upper()]
        except KeyError:
            raise KeyError(f"no conversion rate configured for {currency!r}") from None


def _resolve(root: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else root / p


def load_config(path: str | os.PathLike | None = None,
                root: str | os.PathLike | None = None) -> Config:
    root_path = Path(root or os.environ.get("PRICESYNC_ROOT", ".")).resolve()
    if path is None:
        path = os.environ.get("PRICESYNC_CONFIG") or root_path / DEFAULT_CONFIG
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)

    catalog = raw.get("catalog", {})
    feeds = raw.get("feeds", {})
    sig = raw.get("signature", {})

    base = str(catalog.get("base_currency", "EUR")).upper()
    rates = {str(k).upper(): Decimal(str(v)) for k, v in raw.get("rates", {}).items()}
    rates.setdefault(base, Decimal(1))

    return Config(
        root=root_path,
        db_path=_resolve(root_path, catalog.get("db_path", "var/catalog.db")),
        base_currency=base,
        incoming=_resolve(root_path, feeds.get("incoming", "feeds/incoming")),
        archive=_resolve(root_path, feeds.get("archive", "feeds/archive")),
        quarantine=_resolve(root_path, feeds.get("quarantine", "quarantine")),
        signature=SignaturePolicy(
            enforce=bool(sig.get("enforce", True)),
            keyring=_resolve(root_path, sig.get("keyring", "keys/supplier_keys.json")),
        ),
        rates=rates,
    )
