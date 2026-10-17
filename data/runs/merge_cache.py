"""Merges incoming teammate cache zips into local ./cache without overwriting existing entries."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path


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


def merge_zip(zip_path: Path, cache_dir: Path) -> int:
    added = 0
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            name = member.filename.replace("\\", "/")
            # Handle if zip contains 'cache/...' or just '<hash[:2]>/<hash>.json'
            if name.startswith("cache/"):
                rel_path = name[len("cache/"):]
            else:
                rel_path = name

            dest = cache_dir / rel_path
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(member.filename))
                added += 1

    return added


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
        zips_to_process = list(incoming_dir.glob("*.zip"))

    if not zips_to_process:
        print("No zip files found to merge.")
        run_check_cache()
        return 0

    total_added = 0
    for zp in zips_to_process:
        added = merge_zip(zp, cache_dir)
        total_added += added
        print(f"Merged {zp.name}: added {added} new cache entries (skipped existing).")

    print(f"Total new entries added: {total_added}")
    run_check_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
