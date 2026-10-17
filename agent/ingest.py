"""Northwind ingest: corpus slice -> Surveyor -> structural merge -> faultline:northwind.

    python -m agent.ingest [--scope demo|day1] [--workers 3] [--dry-run]

Order matters. The Surveyor's loader replaces the tenant graph with sources and claims;
`data.seed --merge` then adds Person, System, Decision and their edges on top without
duplicating the Document, Ticket and Message nodes (Dev C's merge mode exists for this).

Scopes:
  demo  the 24 planted documents and 36 same-domain distractors (doc-0001..doc-0060), the
        first 20 tickets, the 4 planted messages and the first 16 other messages that pass
        Dev C's strict message filter. About 100 sources: one Groq free-tier session.
  day1  every document and ticket (712 sources). Several hours on the free tier.

The slice is chosen by id ranges and the message filter, never by reading the answer key,
except that the 4 planted message ids are included so the undocumented kind can occur.
That is disclosed here because it is the one place the key shapes the input.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "out" / "corpus.json"
GROUND_TRUTH = ROOT / "data" / "out" / "ground_truth.json"
OUT_DIR = ROOT / "data" / "out"  # gitignored generator output


def build_slice(scope: str) -> dict:
    if not CORPUS.exists():
        raise SystemExit(f"{CORPUS} not found. Run `uv run --env-file .env python -m data.generate` first.")
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    docs = sorted(corpus["documents"], key=lambda d: d["id"])
    tickets = sorted(corpus.get("tickets", []), key=lambda t: t["id"])
    messages = sorted(corpus.get("messages", []), key=lambda m: m["id"])

    if scope == "day1":
        return {"documents": docs, "tickets": tickets, "messages": []}

    from data.message_filter import filter_messages

    truth = json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))
    planted_msgs = {s for c in truth["conflicts"] for s in (c["source_a_id"], c["source_b_id"]) if s.startswith("msg-")}
    informative = [m for m in filter_messages(messages) if m["id"] not in planted_msgs][:16]
    chosen_msgs = [m for m in messages if m["id"] in planted_msgs] + informative
    return {
        "documents": [d for d in docs if d["id"] <= "doc-0060"],
        "tickets": tickets[:20],
        "messages": sorted(chosen_msgs, key=lambda m: m["id"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=["demo", "day1"], default="demo")
    ap.add_argument("--tenant", default="northwind")
    ap.add_argument("--workers", type=int, default=3, help="Groq free tier is 8k tokens/min; more workers only queue")
    ap.add_argument("--dry-run", action="store_true", help="write the slice and stop")
    args = ap.parse_args()

    corpus = build_slice(args.scope)
    path = OUT_DIR / f"northwind-{args.scope}.json"
    path.write_text(json.dumps(corpus, indent=1), encoding="utf-8")
    n = {k: len(v) for k, v in corpus.items()}
    print(f"slice {args.scope}: {n['documents']} documents, {n['tickets']} tickets, {n['messages']} messages -> {path}")
    if args.dry_run:
        return 0

    from agent.surveyor import run
    from data.seed import seed_structural_graph

    t0 = time.perf_counter()
    out = run(path, args.tenant, args.workers)
    rep = out["report"]
    print(json.dumps({"raw": rep.raw, "kept": rep.kept, "dropped": {k: len(v) for k, v in rep.dropped.items()},
                      "failed": rep.failed_sources, "calls": rep.calls, "entities": len(out["entities"]),
                      "entities_merged_by_consolidation": out["merged"],
                      "near_duplicate_entities": len(out["near"]), "resolver_fallbacks": out["fallbacks"],
                      "timing_s": {k: round(v, 1) for k, v in out["timing"].items()}}, indent=1))

    res = seed_structural_graph(tenant_id=args.tenant, merge=True)
    print("structural merge:", json.dumps({k: v for k, v in res.items() if k != "schema"}, default=str)[:600])
    print(f"ingest done in {time.perf_counter() - t0:.0f}s. Next: python -m agent.adjudicator")
    return 0


if __name__ == "__main__":
    sys.exit(main())
