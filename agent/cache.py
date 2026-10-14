"""Disk cache for every LLM call (CONTRACT §6, rule 7). Mandatory, not an optimisation.

Key = sha256 over (model, op, prompt, content, params). One JSON file per response under
/cache/<k[:2]>/<k>.json. Only successful responses are written; errors are never cached.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"


def cache_dir() -> Path:
    return Path(os.environ.get("FAULTLINE_CACHE_DIR", DEFAULT_CACHE_DIR))


def cache_key(model: str, op: str, prompt: str, content: str, params: dict[str, Any] | None = None) -> str:
    # Canonical JSON so key order and whitespace never change the hash.
    blob = json.dumps({"model": model, "op": op, "prompt": prompt, "content": content,
                       "params": params or {}}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _path(key: str) -> Path:
    return cache_dir() / key[:2] / f"{key}.json"


def get(key: str) -> Any | None:
    p = _path(key)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))["response"]


def put(key: str, response: Any, meta: dict[str, Any]) -> None:
    p = _path(key)
    p.parent.mkdir(parents=True, exist_ok=True)
    record = {"key": key, "cached_at": int(time.time()), **meta, "response": response}
    # Write-then-rename so a crash mid-write never leaves a truncated entry that reads as a hit.
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False)
    os.replace(tmp, p)
