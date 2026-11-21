"""Feed signature verification.

Every supplier signs its feeds with an HMAC-SHA256 key shared with us out of
band. Keys live in the keyring file (keys/supplier_keys.json); each key says
which supplier owns it, which feed formats it may sign, and whether it is
still active.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from pathlib import Path

from .feed import FORMAT_V1, FORMAT_V2, Feed, UnsupportedFormat


class SignatureError(Exception):
    """The feed's signature is missing, unknown, or does not match."""


@dataclass(frozen=True)
class Key:
    key_id: str
    supplier: str
    formats: tuple[int, ...]
    status: str
    secret: bytes

    @property
    def active(self) -> bool:
        return self.status == "active"


class Keyring:
    def __init__(self, keys: dict[str, Key]):
        self._keys = keys

    @classmethod
    def load(cls, path: str | Path) -> "Keyring":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        keys = {}
        for key_id, entry in data.get("keys", {}).items():
            keys[key_id] = Key(
                key_id=key_id,
                supplier=entry["supplier"],
                formats=tuple(int(f) for f in entry.get("formats", [1])),
                status=entry.get("status", "active"),
                secret=bytes.fromhex(entry["secret_hex"]),
            )
        return cls(keys)

    def get(self, key_id: str) -> Key:
        try:
            return self._keys[key_id]
        except KeyError:
            raise SignatureError(f"unknown key id {key_id!r}") from None

    def legacy_key_for(self, supplier: str) -> Key:
        """v1 feeds do not name their key: use the supplier's active v1 key."""
        for key in self._keys.values():
            if key.supplier == supplier and 1 in key.formats and key.active:
                return key
        raise SignatureError(f"no active v1 key for supplier {supplier!r}")


def canonical_v1(raw: dict) -> bytes:
    return json.dumps(raw["items"], sort_keys=True, separators=(",", ":")).encode("utf-8")


def _hmac(secret: bytes, payload: bytes) -> bytes:
    return hmac.new(secret, payload, hashlib.sha256).digest()


def verify_feed(feed: Feed, keyring: Keyring) -> Key:
    """Raise SignatureError unless the feed is signed by a valid key.

    Returns the key that verified the feed.
    """
    if not feed.signature:
        raise SignatureError("feed is not signed")
    if feed.format == FORMAT_V1:
        key = keyring.legacy_key_for(feed.supplier)
        expected = _hmac(key.secret, canonical_v1(feed.raw)).hex()
        if not hmac.compare_digest(expected, feed.signature.lower()):
            raise SignatureError(f"signature mismatch (key {key.key_id})")
        return key
    if feed.format == FORMAT_V2:
        raise UnsupportedFormat("signature verification for supplier-feed/2 is not implemented")
    raise UnsupportedFormat(f"cannot verify format {feed.format!r}")
