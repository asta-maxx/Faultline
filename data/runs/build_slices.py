"""Builds 4 balanced run slices for teammates to parallelise extraction across Groq free tiers."""

from __future__ import annotations

import json
from pathlib import Path
from agent import cache, llm, surveyor


def estimate_tokens(text: str) -> int:
    """Approximate token count (characters / 4)."""
    return max(1, len(text) // 4)


def build_slices() -> list[Path]:
    root = Path(__file__).resolve().parent.parent.parent
    day2_path = root / "data" / "runs" / "day2.json"
    runs_dir = root / "data" / "runs"

    day2 = json.loads(day2_path.read_text(encoding="utf-8"))
    chain = llm._candidates("extract")
    params = {"temperature": 0, "response_format": {"type": "json_object"}}
    sources = surveyor.load_sources(day2)

    uncached = []
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
        if not is_cached:
            uncached.append(s)

    print(f"Total uncached sources to distribute: {len(uncached)}")

    total_tokens = sum(estimate_tokens(s["text"]) for s in uncached)
    target_tokens_per_slice = total_tokens / 4.0
    print(f"Total tokens: ~{total_tokens} (target per slice: ~{int(target_tokens_per_slice)})")

    # Split into 4 slices preserving sequential ID order
    slices_data: list[list[dict]] = [[], [], [], []]
    curr_slice_idx = 0
    curr_tokens = 0

    for s in uncached:
        toks = estimate_tokens(s["text"])
        # Move to next slice if we passed target and not in last slice
        if curr_slice_idx < 3 and (curr_tokens + toks > target_tokens_per_slice) and len(slices_data[curr_slice_idx]) > 0:
            curr_slice_idx += 1
            curr_tokens = 0

        slices_data[curr_slice_idx].append(s)
        curr_tokens += toks

    out_paths = []
    for idx, slice_items in enumerate(slices_data, start=1):
        docs = [{**s["props"], "text": s["text"]} for s in slice_items if s["label"] == "Document"]
        tkts = [{**s["props"]} for s in slice_items if s["label"] == "Ticket"]
        msgs = [{**s["props"]} for s in slice_items if s["label"] == "Message"]

        slice_payload = {
            "documents": docs,
            "tickets": tkts,
            "messages": msgs,
        }

        tok_est = sum(estimate_tokens(s["text"]) for s in slice_items)
        out_file = runs_dir / f"slice_{idx}.json"
        out_file.write_text(json.dumps(slice_payload, indent=2), encoding="utf-8")
        out_paths.append(out_file)
        print(f"Wrote {out_file.name}: {len(docs)} docs, {len(tkts)} tickets, {len(msgs)} messages (~{tok_est} tokens)")

    return out_paths


if __name__ == "__main__":
    build_slices()
