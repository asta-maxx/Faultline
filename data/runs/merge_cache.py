"""Merges incoming teammate cache zips into local ./cache safely with zip-slip protection."""

from __future__ import annotations

import argparse
import collections
import json
import re
import stat
import sys
import zipfile
from pathlib import Path

MAX_ENTRY_SIZE_BYTES = 5 * 1024 * 1024       # 5 MB
MAX_TOTAL_UNCOMPRESSED_BYTES = 500 * 1024 * 1024  # 500 MB


def run_check_cache() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    day2_file = root / "data" / "runs" / "day2.json"
    if not day2_file.exists():
        print(f"Error: {day2_file} not found.")
        return

    from agent import cache, llm, surveyor

    day2 = json.loads(day2_file.read_text(encoding="utf-8"))
    chain = llm._candidates("extract")
    params = {"temperature": 0, "response_format": {"type": "json_object"}}
    sources = surveyor.load_sources(day2)

    docs = day2.get("documents", [])
    tkts = day2.get("tickets", [])
    msgs = day2.get("messages", [])

    cached_docs = 0
    cached_tkts = 0
    cached_msgs = 0

    for s in sources:
        content = f"Document id: {s['id']}\n\n{s['text']}"
        is_cached = False
        for spec in chain:
            k = cache.cache_key(spec, "generate", surveyor.EXTRACT_PROMPT, content, params)
            if cache.get(k) is not None:
                is_cached = True
                break
            k_rh = cache.cache_key(spec, "generate", surveyor.EXTRACT_PROMPT, content, {**params, **surveyor.REASONING_HEAVY})
            if cache.get(k_rh) is not None:
                is_cached = True
                break
        if is_cached:
            if s["label"] == "Document":
                cached_docs += 1
            elif s["label"] == "Ticket":
                cached_tkts += 1
            elif s["label"] == "Message":
                cached_msgs += 1

    total_sources = len(docs) + len(tkts) + len(msgs)
    total_cached = cached_docs + cached_tkts + cached_msgs

    print("\n--- Cache Verification ---")
    print(f"Documents: {cached_docs} / {len(docs)}")
    print(f"Tickets:   {cached_tkts} / {len(tkts)}")
    print(f"Messages:  {cached_msgs} / {len(msgs)}")
    print(f"Total:     {total_cached} / {total_sources} ({total_cached / total_sources:.1%})")


def merge_zip(zip_path: Path, cache_dir: Path) -> tuple[int, dict[str, int]]:
    """Safely extracts .json cache files from zip_path into cache_dir with Zip-Slip protection.

    Returns:
        (added_count, rejected_reasons_dict)
    """
    cache_dir_resolved = cache_dir.resolve()
    added = 0
    rejected: dict[str, int] = collections.defaultdict(int)

    with zipfile.ZipFile(zip_path, "r") as zf:
        # Cap total uncompressed size (prevent zip bomb)
        total_uncompressed = sum(m.file_size for m in zf.infolist())
        if total_uncompressed > MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise ValueError(
                f"Zip uncompressed size ({total_uncompressed} bytes) exceeds limit of {MAX_TOTAL_UNCOMPRESSED_BYTES} bytes"
            )

        for member in zf.infolist():
            if member.is_dir():
                continue

            # 1. Normalise backslashes to forward slashes BEFORE any traversal check
            raw_name = member.filename.replace("\\", "/")

            # 2. Reject symlink entries
            mode = member.external_attr >> 16
            if mode != 0 and stat.S_ISLNK(mode):
                rejected["symlink entry"] += 1
                continue

            # 3. Accept ONLY .json files
            if not raw_name.lower().endswith(".json"):
                rejected["not a .json file"] += 1
                continue

            # 4. Reject absolute paths or drive letters
            if raw_name.startswith("/") or re.match(r"^[a-zA-Z]:", raw_name):
                rejected["absolute path or drive letter"] += 1
                continue

            # 5. Reject any ".." component
            parts = raw_name.split("/")
            if ".." in parts:
                rejected["path traversal component (..)"] += 1
                continue

            # 6. Cap each entry size at 5 MB
            if member.file_size > MAX_ENTRY_SIZE_BYTES:
                rejected["file size exceeds 5MB limit"] += 1
                continue

            # Handle optional leading 'cache/' prefix
            if raw_name.startswith("cache/"):
                rel_path = raw_name[len("cache/"):]
            else:
                rel_path = raw_name

            rel_parts = rel_path.split("/")
            if not rel_path or rel_path.startswith("/") or ".." in rel_parts:
                rejected["invalid relative path"] += 1
                continue

            # 7. Resolve target and require staying inside resolved cache directory
            target = (cache_dir / rel_path).resolve()
            if not target.is_relative_to(cache_dir_resolved):
                rejected["target path outside cache directory"] += 1
                continue

            # 8. Never overwrite existing files
            if target.exists():
                rejected["already exists (not overwritten)"] += 1
                continue

            # Extract file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(member.filename))
            added += 1

    return added, dict(rejected)


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge cache zip into local ./cache")
    parser.add_argument("zip_file", nargs="?", default=None, help="Path to zip file to merge")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent.parent
    cache_dir = root / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    zips_to_process: list[Path] = []
    if args.zip_file:
        p = Path(args.zip_file)
        if not p.is_absolute():
            p = root / p
        if not p.exists():
            print(f"File not found: {p}")
            return 1
        zips_to_process.append(p)
    else:
        incoming_dir = root / "data" / "incoming"
        incoming_dir.mkdir(parents=True, exist_ok=True)
        zips_to_process = sorted(incoming_dir.glob("*.zip"))

    if not zips_to_process:
        print("No zip files found to merge.")
        run_check_cache()
        return 0

    total_added = 0
    total_rejected: dict[str, int] = collections.defaultdict(int)

    for zp in zips_to_process:
        try:
            added, rejected = merge_zip(zp, cache_dir)
            total_added += added
            for r, c in rejected.items():
                total_rejected[r] += c
            print(f"Merged {zp.name}: added {added} entries. Rejected: {dict(rejected)}")
        except Exception as e:
            print(f"Failed to process {zp.name}: {e}")

    print(f"\nTotal new entries added: {total_added}")
    print(f"Total rejected entries: {dict(total_rejected)}")
    run_check_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
