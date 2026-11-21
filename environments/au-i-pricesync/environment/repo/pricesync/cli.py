"""Command line entry point: python -m pricesync <command>.

  sync [FEED ...]   verify and import feeds (default: everything in incoming/)
  show SKU          print the catalog entry for a SKU
  log               print recent sync history
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from .catalog import Catalog
from .config import load_config
from .feed import FeedError, UnsupportedFormat, load_feed
from .signing import Keyring, SignatureError, verify_feed

EXIT_OK, EXIT_ERROR, EXIT_REJECTED = 0, 1, 2


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _move(path: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / path.name
    if path.resolve() != target.resolve():
        shutil.move(str(path), target)
    return target


def sync_one(path: Path, cfg, keyring: Keyring, catalog: Catalog) -> int:
    now = _now()
    try:
        feed = load_feed(path)
    except UnsupportedFormat as exc:
        print(f"error: {path.name}: {exc}", file=sys.stderr)
        catalog.log_sync(path.name, "error", now, detail=str(exc))
        return EXIT_ERROR
    except FeedError as exc:
        print(f"error: {path.name}: malformed feed: {exc}", file=sys.stderr)
        catalog.log_sync(path.name, "error", now, detail=str(exc))
        return EXIT_ERROR

    if feed.notice:
        print(f"[{feed.supplier}] supplier notice: {feed.notice}")

    try:
        key = verify_feed(feed, keyring)
        print(f"{path.name}: signature ok (key {key.key_id})")
    except (SignatureError, UnsupportedFormat) as exc:
        if cfg.signature.enforce:
            dest = _move(path, cfg.quarantine)
            dest.with_suffix(dest.suffix + ".reason").write_text(f"{now} {exc}\n")
            print(f"rejected: {path.name}: signature verification failed: {exc} "
                  f"(moved to {dest.relative_to(cfg.root) if dest.is_relative_to(cfg.root) else dest})",
                  file=sys.stderr)
            catalog.log_sync(path.name, "rejected", now, feed, str(exc))
            return EXIT_REJECTED
        print(f"warning: {path.name}: signature not verified ({exc}); "
              f"importing because [signature] enforce = false", file=sys.stderr)

    try:
        stats = catalog.apply_feed(feed, cfg.base_currency, cfg.rates, now)
    except KeyError as exc:
        print(f"error: {path.name}: {exc}", file=sys.stderr)
        catalog.log_sync(path.name, "error", now, feed, str(exc))
        return EXIT_ERROR
    catalog.log_sync(path.name, "applied", now, feed, str(stats))
    if path.resolve().is_relative_to(cfg.incoming.resolve()):
        _move(path, cfg.archive)
    print(f"{path.name}: applied ({stats})")
    return EXIT_OK


def cmd_sync(args, cfg) -> int:
    paths = [Path(p) for p in args.feeds] or sorted(cfg.incoming.glob("*.json"))
    if not paths:
        print("nothing to sync")
        return EXIT_OK
    keyring = Keyring.load(cfg.signature.keyring)
    worst = EXIT_OK
    with Catalog(cfg.db_path) as catalog:
        for path in paths:
            if not path.exists():
                print(f"error: {path}: no such file", file=sys.stderr)
                worst = max(worst, EXIT_ERROR)
                continue
            worst = max(worst, sync_one(path, cfg, keyring, catalog))
    return worst


def cmd_show(args, cfg) -> int:
    with Catalog(cfg.db_path) as catalog:
        product = catalog.product(args.sku)
    if product is None:
        print(f"{args.sku}: not in catalog", file=sys.stderr)
        return EXIT_ERROR
    breaks = product.pop("breaks")
    for k, v in product.items():
        print(f"{k:18} {v}")
    for br in breaks:
        print(f"  break >= {br['min_qty']:<6} {br['unit_price_minor']} ({br['price_base_minor']} base)")
    return EXIT_OK


def cmd_log(args, cfg) -> int:
    with Catalog(cfg.db_path) as catalog:
        for row in catalog.recent_log(args.limit):
            print(f"{row['at']}  {row['status']:9} {row['feed_name']:32} {row['detail'] or ''}")
    return EXIT_OK


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="pricesync")
    parser.add_argument("--config", help="path to config TOML")
    sub = parser.add_subparsers(dest="command", required=True)
    p_sync = sub.add_parser("sync")
    p_sync.add_argument("feeds", nargs="*")
    p_show = sub.add_parser("show")
    p_show.add_argument("sku")
    p_log = sub.add_parser("log")
    p_log.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    return {"sync": cmd_sync, "show": cmd_show, "log": cmd_log}[args.command](args, cfg)
