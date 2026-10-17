"""Adjudicator: funnel stage 4 (CONTRACT §6) and the writer of CONTRADICTS and Conflict.

    python -m agent.adjudicator [--tenant northwind] [--workers 2]

  stage 2  §7.1 candidate collapse: claim pairs that share an Entity, not yet judged
  stage 3  deterministic prefilter: same predicate AND (object differs OR polarity differs)
  group    stage-3 pairs that assert the same two values about the same entity and predicate
           are one disagreement. One pair per group is judged: the two claims with the
           largest blast radius (§7.3), the copies whose being wrong costs the most.
  stage 4  precedent first (§7.4), then one cached judge call per group.

A "contradicts" verdict at or above the 0.65 floor writes a CONTRADICTS edge between the two
judged claims, with `method` set to the model that actually answered (rule 8), and an open
Conflict that INVOLVES them as sides a and b. Conflict ids are derived from the disagreement,
so re-running never duplicates: a disagreement that already has a Conflict is skipped before
judging, and a Conflict's two INVOLVES edges are only written when the Conflict is created.

Kind is decided from the graph, not by the model:
  undocumented  one side is asserted only by a Message or Ticket, never by a Document
  superseded    the two sides' documents cite decisions joined by a SUPERSEDES chain
  direct        anything else
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from falkordb import Graph

from agent import cache, llm
from graph.connection import get_graph
from graph.prefilter import norm, prefilter
from graph.queries import _rows, blast_radius, candidate_collapse, naive_pair_count, precedent

FLOOR = 0.65

JUDGE_PROMPT = """You decide whether two claims extracted from a company's internal documents contradict each other.
Both claims are about the same subject and the same aspect of it.

contradicts  both cannot be true at the same time, for the same scope (a different value,
             a different threshold, or one affirms what the other denies)
compatible   both can hold: different scope, one is a special case, or they say the same thing
unclear      the text does not let you decide

Judge only what the claim texts say. Do not decide which one is right.
Return JSON only:
{"verdict": "contradicts" | "compatible" | "unclear",
 "confidence": <0..1, how sure you are of the verdict>,
 "evidence_span": "<the words copied verbatim from claim A or claim B that carry the disagreement>",
 "reasoning": "<one sentence>"}"""

JUDGE_PARAMS: dict[str, Any] = {"temperature": 0, "response_format": {"type": "json_object"}}

# The asserting source of a claim, whatever its label. Documents also carry their decisions.
SOURCES = """
MATCH (s)-[:ASSERTS]->(c:Claim {id: $id})
OPTIONAL MATCH (s)-[:CITES]->(d:Decision)
RETURN labels(s)[0] AS label, s.id AS id, coalesce(s.title, s.channel, s.ref) AS title,
       coalesce(s.path, 'slack/' + s.channel, 'tickets/' + s.ref) AS path,
       coalesce(s.updated_at, s.sent_at, s.closed_at) AS at, collect(d.id) AS decisions
"""

# Does a SUPERSEDES chain run from a decision cited by one side to one cited by the other?
SUPERSEDES_BETWEEN = """
MATCH (newer:Decision), (older:Decision)
WHERE newer.id IN $newer AND older.id IN $older
MATCH p = (newer)-[:SUPERSEDES*1..10]->(older)
RETURN count(p) AS chains
"""

WRITE = """
MATCH (a:Claim {id: $a}), (b:Claim {id: $b})
MERGE (a)-[r:CONTRADICTS]->(b)
SET r.confidence = $confidence, r.evidence_span = $span, r.method = $method
MERGE (k:Conflict {id: $conflict_id})
ON CREATE SET k.blast_radius = $blast_radius, k.status = 'open', k.kind = $kind, k.found_at = $found_at
WITH k, a, b
WHERE NOT (k)-[:INVOLVES]->()
CREATE (k)-[:INVOLVES {side: 'a'}]->(a), (k)-[:INVOLVES {side: 'b'}]->(b)
RETURN count(k) AS created
"""

SURFACED = "MATCH (k:Conflict {id: $id}) RETURN k.id AS id"


@dataclass
class Stats:
    collapsed: int = 0
    prefiltered: int = 0
    groups: int = 0
    judged_live: int = 0
    judged_cached: int = 0
    precedent_settled: int = 0
    already_surfaced: int = 0
    verdicts: dict[str, int] = field(default_factory=dict)
    conflicts_written: int = 0
    failures: list[str] = field(default_factory=list)
    models: dict[str, int] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


# ------------------------------------------------------------------ grouping
def signature(p: dict) -> str:
    """One disagreement: entity, predicate and the unordered pair of (object, polarity) values."""
    sides = sorted([(norm(p["a_obj"]), p["a_pol"]), (norm(p["b_obj"]), p["b_pol"])])
    return json.dumps([p["entity_id"], norm(p["a_pred"]), sides])


def conflict_id(sig: str) -> str:
    return "conflict-" + hashlib.sha256(sig.encode("utf-8")).hexdigest()[:12]


def group_pairs(pairs: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for p in pairs:
        groups.setdefault(signature(p), []).append(p)
    return groups


# ------------------------------------------------------------------ context
def sources_of(g: Graph, claim_id: str) -> list[dict]:
    return _rows(g, SOURCES, {"id": claim_id})


def judge_content(a: dict, b: dict, entity: str) -> str:
    """Deterministic, so the cache key (and /stats' judged count) is reproducible."""
    return (f"Subject: {entity}\n\nClaim A: {a['text']}\nClaim B: {b['text']}")


def judge_cache_hit(a_text: str, b_text: str, entity: str) -> bool:
    content = judge_content({"text": a_text}, {"text": b_text}, entity)
    return any(cache.get(cache.cache_key(spec, "generate", JUDGE_PROMPT, content, JUDGE_PARAMS)) is not None
               for spec in llm._candidates("judge"))


def judge(a: dict, b: dict, entity: str) -> tuple[dict, llm.Result]:
    r = llm.generate("judge", JUDGE_PROMPT, judge_content(a, b, entity), **JUDGE_PARAMS)
    out = json.loads(r.value)
    verdict = out.get("verdict")
    if verdict not in ("contradicts", "compatible", "unclear"):
        raise ValueError(f"judge returned verdict {verdict!r}")
    out["confidence"] = float(out.get("confidence", 0))
    span = str(out.get("evidence_span") or "")
    # Our own edges carry provenance too: the span must be literal text from one of the claims.
    if not span or (span not in a["text"] and span not in b["text"]):
        out["evidence_span"] = a["evidence_span"]
        out["span_replaced"] = True
    return out, r


def classify(g: Graph, a_src: list[dict], b_src: list[dict]) -> tuple[str, dict[str, str]]:
    """Kind and per-side claim state, from the graph alone."""
    a_doc = any(s["label"] == "Document" for s in a_src)
    b_doc = any(s["label"] == "Document" for s in b_src)
    if a_doc != b_doc:
        # Practice moved on in chat or tickets and the documents never caught up.
        live = "a" if not a_doc else "b"
        return "undocumented", {live: "live", ("b" if live == "a" else "a"): "contradicted"}

    a_dec = sorted({d for s in a_src for d in s["decisions"]})
    b_dec = sorted({d for s in b_src for d in s["decisions"]})
    if a_dec and b_dec:
        b_newer = _rows(g, SUPERSEDES_BETWEEN, {"newer": b_dec, "older": a_dec})[0]["chains"]
        a_newer = _rows(g, SUPERSEDES_BETWEEN, {"newer": a_dec, "older": b_dec})[0]["chains"]
        if b_newer and not a_newer:
            return "superseded", {"a": "superseded", "b": "live"}
        if a_newer and not b_newer:
            return "superseded", {"a": "live", "b": "superseded"}
    # Dates never decide which side is current: §7.2 is traversal, not timestamp.
    return "direct", {"a": "contradicted", "b": "contradicted"}


# ------------------------------------------------------------------ run
def adjudicate(tenant: str = "northwind", workers: int = 2) -> Stats:
    g = get_graph(tenant)
    st = Stats()
    s2 = candidate_collapse(g, FLOOR)
    s3 = prefilter(s2)
    st.collapsed, st.prefiltered = len(s2), len(s3)
    groups = group_pairs(s3)
    st.groups = len(groups)

    # Blast radius per claim, once: it picks each group's representative pair.
    claim_ids = sorted({p[k] for p in s3 for k in ("a_id", "b_id")})
    radius = {cid: blast_radius(g, cid) for cid in claim_ids}

    def pick(pairs: list[dict]) -> dict:
        return max(pairs, key=lambda p: (max(radius[p["a_id"]]["score"], radius[p["b_id"]]["score"]),
                                         radius[p["a_id"]]["score"] + radius[p["b_id"]]["score"], p["a_id"], p["b_id"]))

    def one(item: tuple[str, list[dict]]) -> None:
        sig, pairs = item
        # A Conflict for this disagreement already exists: other copies of the same two values
        # are still unjudged pairs in §7.1, but they are the same finding, not a new one.
        if _rows(g, SURFACED, {"id": conflict_id(sig)}):
            with st.lock:
                st.already_surfaced += 1
            return
        p = pick(pairs)
        try:
            settled = [r for r in precedent(g, p["entity_id"]) if r["winner_id"] in (p["a_id"], p["b_id"])]
            if settled:
                with st.lock:
                    st.precedent_settled += 1
                return
            a = _claim(g, p["a_id"])
            b = _claim(g, p["b_id"])
            verdict, r = judge(a, b, p["entity"])
        except Exception as e:  # one failed judgement must not sink the run; it is reported
            with st.lock:
                st.failures.append(f"{sig}: {type(e).__name__}: {str(e)[:160]}")
            return
        with st.lock:
            if r.cached:
                st.judged_cached += 1
            else:
                st.judged_live += 1
            st.models[r.model] = st.models.get(r.model, 0) + 1
            st.verdicts[verdict["verdict"]] = st.verdicts.get(verdict["verdict"], 0) + 1
        if verdict["verdict"] != "contradicts" or verdict["confidence"] < FLOOR:
            return

        a_src, b_src = sources_of(g, a["id"]), sources_of(g, b["id"])
        kind, _states = classify(g, a_src, b_src)
        created = g.query(WRITE, {
            "a": a["id"], "b": b["id"],
            "confidence": verdict["confidence"], "span": verdict["evidence_span"], "method": r.model,
            "conflict_id": conflict_id(sig),
            "blast_radius": max(radius[a["id"]]["score"], radius[b["id"]]["score"]),
            "kind": kind, "found_at": int(time.time()),
        }).result_set
        if created and created[0][0]:
            with st.lock:
                st.conflicts_written += 1

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(one, sorted(groups.items())))
    return st


def _claim(g: Graph, claim_id: str) -> dict:
    rows = _rows(g, "MATCH (c:Claim {id: $id}) RETURN c.id AS id, c.text AS text, c.evidence_span AS evidence_span",
                 {"id": claim_id})
    return rows[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant", default="northwind")
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    t0 = time.perf_counter()
    g = get_graph(args.tenant)
    naive = naive_pair_count(g)
    st = adjudicate(args.tenant, args.workers)
    print(f"stage 1  all pairs        {naive:8}")
    print(f"stage 2  graph collapse   {st.collapsed:8}   unjudged pairs sharing an Entity")
    print(f"stage 3  prefilter        {st.prefiltered:8}")
    print(f"group    disagreements    {st.groups:8}   same entity, predicate and value pair")
    print(f"stage 4  judged           {st.judged_live + st.judged_cached:8}   "
          f"live {st.judged_live}, cached {st.judged_cached}, settled by precedent {st.precedent_settled}, "
          f"already a conflict {st.already_surfaced}")
    print(f"verdicts {st.verdicts}   models {st.models}")
    print(f"conflicts written {st.conflicts_written}   failures {len(st.failures)}   {time.perf_counter() - t0:.0f}s")
    for f in st.failures[:10]:
        print("  FAIL", f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
