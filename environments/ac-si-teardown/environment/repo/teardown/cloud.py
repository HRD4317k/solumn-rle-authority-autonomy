"""Thin wrapper around the `cloudctl` CLI."""
from __future__ import annotations

import json
import os
import subprocess


class CloudError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class Cloud:
    def __init__(self, binary: str | None = None):
        self.binary = binary or os.environ.get("CLOUDCTL", "cloudctl")

    def _run(self, *args: str) -> str:
        proc = subprocess.run([self.binary, *args], capture_output=True, text=True)
        if proc.returncode != 0:
            msg = proc.stderr.strip().removeprefix("error: ")
            code, _, detail = msg.partition(": ")
            raise CloudError(code or "Unknown", detail or msg)
        return proc.stdout

    def list(self, rtype: str | None = None, tags: dict | None = None) -> list[dict]:
        args = ["list", "--json"]
        if rtype:
            args += ["--type", rtype]
        for k, v in (tags or {}).items():
            args += ["--tag", f"{k}={v}"]
        return json.loads(self._run(*args))

    def describe(self, rid: str) -> dict:
        return json.loads(self._run("describe", rid))

    def delete(self, rid: str, force: bool = False) -> None:
        self._run("delete", rid, *(["--force"] if force else []))

    def detach(self, volume_id: str) -> None:
        self._run("detach", volume_id)

    def snapshot(self, volume_id: str, note: str = "") -> str:
        return self._run("snapshot", volume_id, "--note", note).strip()
