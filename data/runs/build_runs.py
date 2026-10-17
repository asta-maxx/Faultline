"""Generates run files for incremental/cumulative surveyor passes."""

from __future__ import annotations

import json
from pathlib import Path


def build_sample_run(corpus_path: Path, out_path: Path) -> None:
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    docs = sorted([d for d in corpus["documents"] if d["id"] <= "doc-0015"], key=lambda x: x["id"])[:15]
    tkts = sorted([t for t in corpus.get("tickets", []) if t["id"] <= "tkt-0015"], key=lambda x: x["id"])[:15]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_data = {
        "documents": docs,
        "tickets": tkts,
        "messages": [],
    }
    out_path.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} with {len(docs)} documents and {len(tkts)} tickets.")


def build_day1_run(corpus_path: Path, out_path: Path) -> None:
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    docs = sorted(corpus["documents"], key=lambda x: x["id"])
    tkts = sorted(corpus.get("tickets", []), key=lambda x: x["id"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_data = {
        "documents": docs,
        "tickets": tkts,
        "messages": [],
    }
    out_path.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} with {len(docs)} documents and {len(tkts)} tickets.")


def build_day2_run(corpus_path: Path, day1_path: Path, out_path: Path, message_ids: list[str] | None = None, limit_messages: int | None = None) -> None:
    day1_data = json.loads(day1_path.read_text(encoding="utf-8"))
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    all_msgs = sorted(corpus.get("messages", []), key=lambda x: x["id"])
    
    if message_ids is not None:
        target_ids = set(message_ids)
        selected_msgs = [m for m in all_msgs if m["id"] in target_ids]
    else:
        selected_msgs = all_msgs
        
    if limit_messages is not None:
        selected_msgs = selected_msgs[:limit_messages]

    out_data = {
        "documents": day1_data["documents"],
        "tickets": day1_data["tickets"],
        "messages": selected_msgs,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} with {len(out_data['documents'])} docs, {len(out_data['tickets'])} tickets, {len(selected_msgs)} messages.")


if __name__ == "__main__":
    import argparse
    from data.message_filter import filter_messages

    root = Path(__file__).resolve().parent.parent.parent
    corpus_p = root / "data" / "out" / "corpus.json"
    runs_dir = root / "data" / "runs"

    parser = argparse.ArgumentParser(description="Build cumulative run files for surveyor.")
    parser.add_argument("--sample", action="store_true", help="Build sample.json (15 docs + 15 tickets)")
    parser.add_argument("--day1", action="store_true", help="Build day1.json (312 docs + 400 tickets)")
    parser.add_argument("--day2", action="store_true", help="Build day2.json (day1 + messages)")
    parser.add_argument("--filtered", action="store_true", help="Filter messages for day2 using message_filter.py")
    parser.add_argument("--include-counts", action="store_true", help="Include broad count units in message filter")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of messages in day2")
    args = parser.parse_args()

    # Default action if no flags provided: build sample and day1
    if not (args.sample or args.day1 or args.day2):
        build_sample_run(corpus_p, runs_dir / "sample.json")
        build_day1_run(corpus_p, runs_dir / "day1.json")
    else:
        if args.sample:
            build_sample_run(corpus_p, runs_dir / "sample.json")
        if args.day1:
            build_day1_run(corpus_p, runs_dir / "day1.json")
        if args.day2:
            day1_file = runs_dir / "day1.json"
            if not day1_file.exists():
                build_day1_run(corpus_p, day1_file)
            if args.filtered:
                corpus = json.loads(corpus_p.read_text(encoding="utf-8"))
                filtered = filter_messages(corpus.get("messages", []), include_count_nouns=args.include_counts)
                msg_ids = [m["id"] for m in filtered]
                build_day2_run(corpus_p, day1_file, runs_dir / "day2.json", message_ids=msg_ids, limit_messages=args.limit)
            else:
                build_day2_run(corpus_p, day1_file, runs_dir / "day2.json", limit_messages=args.limit)

