"""Run the Surveyor on the mini corpus, then the funnel, then score it against the answer key.

    python -m agent.survey_eval [--tenant minicorpus] [--workers 12]

The answer key (planted_contradictions) is read only here, after extraction, never by a prompt.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

from agent.surveyor import FLOOR, run
from graph.connection import get_graph
from graph.prefilter import prefilter
from graph.queries import candidate_collapse, naive_pair_count


def _words(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.lower()))


def matches(claim: dict, side: dict) -> bool:
    """A claim realises a planted side if it comes from that source and its evidence overlaps the planted span."""
    if claim["source_id"] != side["source_id"]:
        return False
    a, b = claim["evidence_span"], side["evidence_span"]
    if a in b or b in a:
        return True
    wa, wb = _words(a), _words(b)
    return bool(wa and wb) and len(wa & wb) / min(len(wa), len(wb)) >= 0.5


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant", default="minicorpus")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()
    out = run(Path("fixtures/mini-corpus.json"), args.tenant, args.workers)
    rep, claims, mapping = out["report"], out["claims"], out["mapping"]
    by_id = {c["id"]: c for c in claims}

    dropped = sum(len(v) for v in rep.dropped.values())
    print(f"sources {len(out['sources'])}   LLM calls live {rep.calls['live']} cached {rep.calls['cached']}   "
          f"time extract {out['timing']['extract']:.1f}s resolve {out['timing']['resolve']:.1f}s "
          f"harmonise {out['timing']['harmonise']:.1f}s")
    if rep.failed_sources:
        print("FAILED:", rep.failed_sources)
    print(f"\nCLAIMS  raw {rep.raw}   kept {rep.kept}   dropped {dropped}  "
          f"(drop rate {dropped / max(rep.raw, 1):.0%})")
    for reason, items in sorted(rep.dropped.items(), key=lambda kv: -len(kv[1])):
        print(f"  {reason:17} {len(items):3}")
        for it in items[:4]:
            print(f"      [{it['source']}] span={it.get('evidence_span', '')!r:.90}"
                  + (f" conf={it.get('confidence')}" if reason == "low_confidence" else ""))

    ents = Counter(c["entity_id"] for c in claims)
    print(f"\nENTITIES  {len(ents)} (from {len(mapping)} raw subject refs)")
    for e, n in ents.most_common():
        aliases = sorted({r for r, m in mapping.items() if m["id"] == e})
        print(f"  {n:3}  {e:42} <- {', '.join(a for a in aliases if a != e) or '-'}")
    print(f"near-duplicate entity pairs: {len(out['near'])}")
    for a, b, ratio, jacc in out["near"]:
        print(f"  ?  {a}  ~  {b}   (name ratio {ratio}, token jaccard {jacc})")

    g = get_graph(args.tenant)
    naive = naive_pair_count(g)
    s2 = candidate_collapse(g, FLOOR)
    s3 = prefilter(s2)
    n = len(claims)
    print(f"\nFUNNEL  faultline:{args.tenant}")
    print(f"  stage 1  all pairs        {naive:6}   n*(n-1)/2 with n = {n}")
    print(f"  stage 2  graph collapse   {len(s2):6}")
    print(f"  stage 3  prefilter        {len(s3):6}")
    print(f"  stage 4  LLM judgement  <={len(s3):6}   (Adjudicator not built; 0 judge calls)")

    pairs2 = {frozenset((p["a_id"], p["b_id"])) for p in s2}
    pairs3 = {frozenset((p["a_id"], p["b_id"])) for p in s3}
    print("\nPLANTED CONTRADICTIONS")
    survived = 0
    for pl in out["corpus"]["planted_contradictions"]:
        A = [c for c in claims if matches(c, pl["a"])]
        B = [c for c in claims if matches(c, pl["b"])]
        combos = [frozenset((a["id"], b["id"])) for a in A for b in B if a["id"] != b["id"]]
        in2 = [p for p in combos if p in pairs2]
        in3 = [p for p in combos if p in pairs3]
        survived += bool(in3)
        if in3:
            verdict = "STAGE 3"
        elif not A or not B:
            verdict = "lost: not extracted (" + ", ".join(s for s, x in (("a", A), ("b", B)) if not x) + ")"
        elif not in2:
            verdict = "lost at stage 2: different entities"
        else:
            verdict = "lost at stage 3: predicate/object/polarity"
        print(f"  {pl['id']} {pl['kind']:12} {verdict}")
        if not in3:
            for side, cs in (("a", A), ("b", B)):
                for c in cs:
                    print(f"      {side}: entity={c['entity_id']} pred={c['predicate']} obj={c['object']!r} pol={c['polarity']}")
    print(f"\n{survived} of {len(out['corpus']['planted_contradictions'])} planted contradictions survive to stage 3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
