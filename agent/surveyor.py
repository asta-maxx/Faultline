"""Surveyor: constrained claim extraction (CONTRACT §6), written directly, not via Graphiti.

    python -m agent.surveyor [corpus.json] [--tenant minicorpus] [--workers 12]

Three LLM phases, all on the extract role (Groq) and all through the disk cache:

  1. extract    one call per source, concurrent. Output is validated in Python and every
                rejected claim is kept with a reason: schema, low_confidence,
                span_not_literal, duplicate.
  2. resolve    one call over every distinct subject: aliases collapse to exactly one
                Entity per real subject (§5). A deterministic pass then flags any
                near-duplicate entities that survived.
  3. harmonise  one call per entity with 2+ claims, concurrent: claims about the same
                aspect get the same predicate. Stage 3 of the funnel only fires on a
                shared predicate, so this is what makes claims comparable.

Then the claims are loaded into faultline:{tenant} with raw Cypher and the funnel runs.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent import llm

FLOOR = 0.65
SUBJECT_TYPES = {"system", "policy", "metric", "process", "artifact"}
SNAKE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")

EXTRACT_PROMPT = """You extract factual claims from one internal company document for a contradiction detector.
Return JSON only: {"claims": [ ... ]}. Each claim has exactly these fields:

  text          one self-contained sentence stating ONE assertion
  polarity      "affirm" or "deny"
  subject_ref   kebab-case slug of the subject, e.g. "payments-ledger"
  subject_name  human name of the subject, e.g. "Payments Ledger"
  subject_type  one of: system, policy, metric, process, artifact
  predicate     snake_case name of the aspect being asserted, e.g. "retry_limit", "timeout", "approval_required"
  object        the value asserted, short, e.g. "3 attempts", "10 seconds", "finance team"
  confidence    0..1, how explicitly the TEXT states it (not whether you believe it)
  evidence_span the shortest span copied VERBATIM from the document that proves the claim

Rules:
- One assertion per claim. A sentence with two facts gives two claims.
- The subject is the specific thing the assertion constrains: the system, the policy or rule,
  the metric, the process, or the artifact. Use the name other documents would also use for
  it, not the document's own title. A rule about a limit or a window is about that policy
  (e.g. "Invoice Approval Window"), not about the team that applies it.
- The predicate names the aspect, not the value: two documents giving different values for the
  same aspect must produce the same predicate.
- For a negative or optional statement keep the predicate and object you would use for the
  positive one and set polarity to "deny" (e.g. "approval is not required" ->
  predicate "approval_required", object "approval", polarity "deny").
- evidence_span must be an exact contiguous substring of the document: same characters,
  same punctuation, no ellipsis, no paraphrase.
- Extract rules, limits, schedules, ownership, thresholds and behaviours. Skip headings,
  questions and build instructions for developers.
"""

RESOLVE_PROMPT = """You resolve entity aliases for a knowledge graph. Every input subject was extracted
independently, so the same real-world subject may appear under several slugs or names.
Merge subjects that denote the SAME real-world system, policy, metric, process or artifact.
Do NOT merge things that are merely related (a system and a policy about it are different;
two different limits on the same system are different policies).

Return JSON only, in this compact shape:
{"entities": {"<canonical kebab-case id>": {"name": "<name>", "type": "<type>"}},
 "map": {"<input subject_ref>": "<canonical id>"}}
Every input subject_ref must appear as a key of "map". type is one of:
system, policy, metric, process, artifact."""

HARMONISE_PROMPT = """You normalise predicates for claims that are all about one subject.
Claims that assert the SAME aspect of the subject must share one identical snake_case predicate,
even if their values differ (that difference is what we are looking for). Claims about different
aspects must keep different predicates. Prefer the clearest existing predicate name.

Return JSON only: {"predicates": {"<claim index>": "<snake_case predicate>", ...}} covering every index."""


@dataclass
class Report:
    raw: int = 0
    kept: int = 0
    dropped: dict[str, list[dict]] = field(default_factory=dict)
    failed_sources: list[tuple[str, str]] = field(default_factory=list)
    calls: dict[str, int] = field(default_factory=lambda: {"live": 0, "cached": 0})
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def drop(self, reason: str, claim: dict, source: str) -> None:
        with self.lock:
            self.dropped.setdefault(reason, []).append({"source": source, **claim})


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# Resolve and harmonise reason over many items at once; gpt-oss can spend its whole output
# budget thinking and return nothing, which Groq reports as json_validate_failed.
REASONING_HEAVY = {"reasoning_effort": "low", "max_completion_tokens": 8192}


def _ask(prompt: str, content: str, rep: Report, **extra: Any) -> dict:
    r = llm.generate("extract", prompt, content, temperature=0, response_format={"type": "json_object"}, **extra)
    with rep.lock:
        rep.calls["cached" if r.cached else "live"] += 1
    return json.loads(r.value)


# ------------------------------------------------------------------ phase 1
def load_sources(corpus: dict) -> list[dict]:
    out = [{"id": d["id"], "label": "Document", "text": d["text"], "props": {k: d[k] for k in
            ("id", "title", "path", "kind", "updated_at")}} for d in corpus["documents"]]
    out += [{"id": m["id"], "label": "Message", "text": m["text"], "props": m} for m in corpus.get("messages", [])]
    out += [{"id": t["id"], "label": "Ticket", "text": f"{t['title']}\n{t['text']}", "props": t}
            for t in corpus.get("tickets", [])]
    return out


def validate(raw: dict, src: dict, rep: Report) -> dict | None:
    need = ("text", "polarity", "subject_ref", "subject_name", "subject_type", "predicate", "object",
            "confidence", "evidence_span")
    if not all(isinstance(raw.get(k), (str, int, float)) and str(raw.get(k)).strip() for k in need):
        rep.drop("schema", raw, src["id"])
        return None
    c = {k: raw[k].strip() if isinstance(raw[k], str) else raw[k] for k in need}
    try:
        c["confidence"] = float(c["confidence"])
    except ValueError:
        rep.drop("schema", raw, src["id"])
        return None
    c["subject_ref"] = slugify(c["subject_ref"])
    if c["polarity"] not in ("affirm", "deny") or c["subject_type"] not in SUBJECT_TYPES \
            or not SNAKE.match(c["predicate"]) or not 0 <= c["confidence"] <= 1:
        rep.drop("schema", raw, src["id"])
        return None
    if c["confidence"] < FLOOR:
        rep.drop("low_confidence", c, src["id"])
        return None
    if c["evidence_span"] not in src["text"]:  # rule 6: literal substring or nothing
        rep.drop("span_not_literal", c, src["id"])
        return None
    c["source_id"] = src["id"]
    c["derived_from"] = None
    return c


def extract_source(src: dict, rep: Report) -> list[dict]:
    try:
        out = _ask(EXTRACT_PROMPT, f"Document id: {src['id']}\n\n{src['text']}", rep)
    except Exception as e:  # one bad source must not sink the run; it is reported
        with rep.lock:
            rep.failed_sources.append((src["id"], f"{type(e).__name__}: {str(e)[:160]}"))
        return []
    raws = out.get("claims", []) if isinstance(out, dict) else []
    with rep.lock:
        rep.raw += len(raws)
    kept, seen = [], set()
    for raw in raws:
        c = validate(raw, src, rep) if isinstance(raw, dict) else None
        if c is None:
            continue
        key = (c["subject_ref"], c["predicate"], c["object"].casefold(), c["polarity"])
        if key in seen:
            rep.drop("duplicate", c, src["id"])
            continue
        seen.add(key)
        kept.append(c)
    return kept


# ------------------------------------------------------------------ phase 2
def resolve_entities(claims: list[dict], rep: Report) -> tuple[dict[str, dict], list[tuple]]:
    subjects: dict[str, dict] = {}
    for c in claims:
        s = subjects.setdefault(c["subject_ref"], {"subject_ref": c["subject_ref"], "name": c["subject_name"],
                                                   "type": c["subject_type"], "examples": []})
        if len(s["examples"]) < 2:
            s["examples"].append(c["text"])
    listing = json.dumps(sorted(subjects.values(), key=lambda s: s["subject_ref"]), indent=1)
    out = _ask(RESOLVE_PROMPT, listing, rep, **REASONING_HEAVY)

    canon = {slugify(k): v for k, v in (out.get("entities") or {}).items() if isinstance(v, dict)}
    mapping: dict[str, dict] = {}
    for ref, target in (out.get("map") or {}).items():
        ref, eid = slugify(str(ref)), slugify(str(target))
        if ref in subjects and eid:
            ent = canon.get(eid, {})
            etype = ent.get("type") if ent.get("type") in SUBJECT_TYPES else subjects[ref]["type"]
            mapping[ref] = {"id": eid, "name": ent.get("name") or subjects[ref]["name"], "type": etype}
    for ref, s in subjects.items():  # anything the model dropped stays its own entity
        mapping.setdefault(ref, {"id": ref, "name": s["name"], "type": s["type"]})
    return mapping, near_duplicates({m["id"]: m["name"] for m in mapping.values()})


def near_duplicates(entities: dict[str, str]) -> list[tuple]:
    """Pairs of surviving entities that look like the same subject. Any hit means the
    collapse query may silently miss pairs, so each one is reported, never auto-merged."""
    stop = {"the", "a", "of", "for", "and", "policy", "process", "system"}
    toks = {e: {t for t in re.split(r"[^a-z0-9]+", f"{e} {n}".lower()) if t and t not in stop}
            for e, n in entities.items()}
    hits = []
    ids = sorted(entities)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            ratio = difflib.SequenceMatcher(None, a, b).ratio()
            ta, tb = toks[a], toks[b]
            jacc = len(ta & tb) / len(ta | tb) if ta | tb else 0
            if ratio >= 0.8 or jacc >= 0.5 or (ta and tb and (ta <= tb or tb <= ta)):
                hits.append((a, b, round(ratio, 2), round(jacc, 2)))
    return hits


# ------------------------------------------------------------------ phase 3
def harmonise(entity_id: str, claims: list[dict], rep: Report) -> None:
    listing = "\n".join(f'{i}. predicate={c["predicate"]} object="{c["object"]}" text="{c["text"]}"'
                        for i, c in enumerate(claims))
    try:
        out = _ask(HARMONISE_PROMPT, f"Subject: {entity_id}\n{listing}", rep, **REASONING_HEAVY).get("predicates", {})
    except Exception as e:
        with rep.lock:
            rep.failed_sources.append((f"harmonise:{entity_id}", f"{type(e).__name__}: {str(e)[:160]}"))
        return
    for i, c in enumerate(claims):
        p = str(out.get(str(i), "")).strip()
        if SNAKE.match(p):
            c["predicate_raw"], c["predicate"] = c["predicate"], p


# ------------------------------------------------------------------ load
def load_graph(tenant: str, sources: list[dict], claims: list[dict], entities: dict[str, dict]) -> None:
    from graph.connection import get_graph
    from graph.schema import apply_schema

    g = get_graph(tenant)
    try:
        g.delete()
    except Exception:
        pass  # graph did not exist yet
    g = get_graph(tenant)
    apply_schema(tenant)
    for label in ("Document", "Message", "Ticket"):
        rows = [s["props"] for s in sources if s["label"] == label]
        if rows:
            props = ", ".join(f"{k}: r.{k}" for k in rows[0])
            g.query(f"UNWIND $rows AS r CREATE (:{label} {{{props}}})", {"rows": rows})
    ents = {e["id"]: e for e in entities.values()}
    g.query("UNWIND $rows AS r CREATE (:Entity {id: r.id, name: r.name, type: r.type})", {"rows": list(ents.values())})
    now = int(time.time())
    rows = [{**{k: c[k] for k in ("id", "text", "polarity", "predicate", "object", "evidence_span", "confidence")},
             "subject_ref": c["entity_id"], "extracted_at": now, "src": c["source_id"]} for c in claims]
    g.query("UNWIND $rows AS r CREATE (:Claim {id: r.id, text: r.text, polarity: r.polarity, subject_ref: r.subject_ref, "
            "predicate: r.predicate, object: r.object, evidence_span: r.evidence_span, confidence: r.confidence, "
            "extracted_at: r.extracted_at})", {"rows": rows})
    g.query("UNWIND $rows AS r MATCH (c:Claim {id: r.id}), (e:Entity {id: r.subject_ref}) CREATE (c)-[:ABOUT]->(e)",
            {"rows": rows})
    g.query("UNWIND $rows AS r MATCH (c:Claim {id: r.id}), (s {id: r.src}) WHERE s:Document OR s:Message OR s:Ticket "
            "CREATE (s)-[:ASSERTS]->(c)", {"rows": rows})


# ------------------------------------------------------------------ run
def run(corpus_path: Path, tenant: str, workers: int) -> dict:
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    sources = load_sources(corpus)
    rep = Report()
    t0 = time.perf_counter()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        claims = [c for batch in pool.map(lambda s: extract_source(s, rep), sources) for c in batch]
    t1 = time.perf_counter()

    for c in claims:  # deterministic ids: same source + span + subject + predicate -> same claim id
        c["id"] = str(uuid.uuid5(uuid.NAMESPACE_URL, "faultline/claim/" + "|".join(
            str(c[k]) for k in ("source_id", "evidence_span", "subject_ref", "predicate", "object", "polarity"))))
    mapping, near = resolve_entities(claims, rep)
    for c in claims:
        c["entity_id"] = mapping[c["subject_ref"]]["id"]
    t2 = time.perf_counter()

    by_entity: dict[str, list[dict]] = {}
    for c in claims:
        by_entity.setdefault(c["entity_id"], []).append(c)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(lambda kv: harmonise(kv[0], kv[1], rep), [kv for kv in by_entity.items() if len(kv[1]) > 1]))
    t3 = time.perf_counter()

    rep.kept = len(claims)
    load_graph(tenant, sources, claims, mapping)
    return {"sources": sources, "claims": claims, "mapping": mapping, "near": near, "report": rep,
            "timing": {"extract": t1 - t0, "resolve": t2 - t1, "harmonise": t3 - t2}, "corpus": corpus}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus", nargs="?", default="fixtures/mini-corpus.json")
    ap.add_argument("--tenant", default="minicorpus")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()
    out = run(Path(args.corpus), args.tenant, args.workers)
    rep = out["report"]
    print(json.dumps({"raw": rep.raw, "kept": rep.kept, "dropped": {k: len(v) for k, v in rep.dropped.items()},
                      "failed": rep.failed_sources, "calls": rep.calls, "timing_s": out["timing"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
