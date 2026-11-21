"""SQLite access and the migration runner.

Migrations live in migrations/ as NNNN_description.sql or NNNN_description.py.
A .py migration defines `upgrade(conn)`. Each version is applied once, in
order, and recorded in schema_migrations. The release pipeline runs exactly
this code against the production database.
"""
from __future__ import annotations

import importlib.util
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
_NAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.(sql|py)$")


class MigrationError(Exception):
    pass


def connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations ("
                 "version TEXT PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)")


def applied_versions(conn: sqlite3.Connection) -> set[str]:
    _ensure_table(conn)
    return {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}


def discover(directory: Path = MIGRATIONS_DIR) -> list[tuple[str, Path]]:
    found: dict[str, Path] = {}
    for path in sorted(directory.iterdir()):
        m = _NAME.match(path.name)
        if not m:
            continue
        version = m.group(1)
        if version in found:
            raise MigrationError(f"two migrations share version {version}: "
                                 f"{found[version].name}, {path.name}")
        found[version] = path
    return sorted(found.items())


def _run_python(conn: sqlite3.Connection, path: Path) -> None:
    spec = importlib.util.spec_from_file_location(f"migration_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "upgrade"):
        raise MigrationError(f"{path.name} has no upgrade(conn)")
    module.upgrade(conn)


def migrate(conn: sqlite3.Connection, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply pending migrations; returns the names applied."""
    done = applied_versions(conn)
    applied = []
    for version, path in discover(directory):
        if version in done:
            continue
        try:
            if path.suffix == ".sql":
                conn.executescript(path.read_text())
            else:
                _run_python(conn, path)
        except Exception as exc:
            conn.rollback()
            raise MigrationError(f"{path.name} failed: {exc}") from exc
        conn.execute("INSERT INTO schema_migrations VALUES (?, ?, ?)",
                     (version, path.name, datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))
        conn.commit()
        applied.append(path.name)
    return applied
