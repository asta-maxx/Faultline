"""Score faultline:northwind against Dev C's answer key (data/out/ground_truth.json).

    python -m agent.northwind_eval [--tenant northwind]

Read only after extraction and adjudication; no prompt ever sees the key. For each planted
contradiction it reports how far the pair got:

  extracted   both planted sources produced a claim that overlaps the planted sentence
  collapsed   two such claims share an Entity (stage 2)
  prefiltered they share a predicate and differ in object or polarity (stage 3)
  judged      a CONTRADICTS edge joins a claim from source a and a claim from source b
  surfaced    an open or resolved Conflict covers that disagreement (same entity and values)
  kind        the Conflict's kind matches the planted kind
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from graph.connection import get_graph
from graph.prefilter import is_likely_contradiction
from graph.queries import rows

TRUTH = Path(__file__).resolve().parent.parent / "data" / "out" / "ground_truth.json"

CLAIMS_FROM = """
MATCH (s {id: $src})-[:ASSERTS]->(c:Claim)-[:ABOUT]->(e:Entity)
RETURN c.id AS id, c.text AS text, c.evidence_span AS span, c.predicate AS pred, c.object AS obj,
       c.polarity AS pol, e.id AS entity
"""

CONTRADICTS = "MATCH (a:Claim)-[:CONTRADICTS]-(b:Claim) WHERE a.id IN $a AND b.id IN $b RETURN count(*) AS n"

CONFLICTS_FOR = """
MATCH (k:Conflict)-[:INVOLVES]->(c:Claim)
WHERE c.id IN $ids
RETURN DISTINCT k.id AS id, k.kind AS kind, k.status AS status, k.blast_radius AS radius
"""


def _words(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def overlaps(claim: dict, planted: str) -> bool:
    a, b = claim["span"], planted
    if a in b or b in a:
        return True
    wa, wb = _words(a), _words(b)
    return bool(wa and wb) and len(wa & wb) / min(len(wa), len(wb)) >= 0.6


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant", default="northwind")
    args = ap.parse_args()
    g = get_graph(args.tenant)
    truth = json.loads(TRUTH.read_text(encoding="utf-8"))

    totals = dict.fromkeys(["extracted", "collapsed", "prefiltered", "judged", "surfaced", "kind"], 0)
    print(f"{'plant':9} {'kind':13} {'reached':12} detail")
    for p in truth["conflicts"]:
        A = [c for c in rows(g, CLAIMS_FROM, {"src": p["source_a_id"]}) if overlaps(c, p["evidence_span_a"])]
        B = [c for c in rows(g, CLAIMS_FROM, {"src": p["source_b_id"]}) if overlaps(c, p["evidence_span_b"])]
        pairs = [(a, b) for a in A for b in B]
        stage = {
            "extracted": bool(A and B),
            "collapsed": any(a["entity"] == b["entity"] for a, b in pairs),
            "prefiltered": any(a["entity"] == b["entity"] and is_likely_contradiction(
                a["pred"], a["obj"], a["pol"], b["pred"], b["obj"], b["pol"]) for a, b in pairs),
            "judged": bool(pairs) and rows(g, CONTRADICTS, {"a": [a["id"] for a in A], "b": [b["id"] for b in B]})[0]["n"] > 0,
        }
        # A Conflict covers the disagreement if it involves any claim asserting either planted value.
        conflicts = rows(g, CONFLICTS_FOR, {"ids": [c["id"] for c in A + B]}) if A or B else []
        stage["surfaced"] = bool(conflicts)
        stage["kind"] = any(k["kind"] == p["kind"] for k in conflicts)
        for k, v in stage.items():
            totals[k] += v
        reached = next((k for k in reversed(list(stage)) if stage[k]), "nothing")
        detail = ""
        if not stage["extracted"]:
            detail = "missing side " + ",".join(s for s, x in (("a", A), ("b", B)) if not x)
        elif not stage["collapsed"]:
            detail = "entities " + " / ".join(sorted({c["entity"] for c in A + B}))
        elif not stage["prefiltered"]:
            detail = "; ".join(f"{a['pred']}={a['obj']!r} vs {b['pred']}={b['obj']!r}" for a, b in pairs[:2])
        elif conflicts:
            detail = ", ".join(f"{k['id']} {k['kind']} {k['radius']}" for k in conflicts[:2])
        print(f"{p['id']:9} {p['kind']:13} {reached:12} {detail}")

    n = len(truth["conflicts"])
    print("\n" + "   ".join(f"{k} {v}/{n}" for k, v in totals.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
