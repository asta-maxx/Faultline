"""Load a small synthetic graph, run the funnel, print all four stage counts.

    FALKOR_URL=redis://localhost:6380 python -m graph.collapse_demo

Loads into tenant graph faultline:synthetic (wiped first), never faultline:northwind.
Stage 2 and stage 3 are each checked against an independent pure-Python brute force
over the same seed data, so the printed numbers are verified, not just reported.
"""

from __future__ import annotations

import sys
import uuid
from itertools import combinations

from graph.connection import get_graph
from graph.prefilter import norm, prefilter
from graph.queries import (
    blast_radius, candidate_collapse, conflict_blast_radius,
    current_claim, naive_pair_count, precedent, traversal_path,
)
from graph.schema import apply_schema

TENANT = "synthetic"
T0 = 1791936000  # 2026-10-14

A, D = "affirm", "deny"
# entity id -> (name, type, [(predicate, object, polarity), ...]). 12 entities, 40 claims.
# Hand count of stage 3 (shared predicate AND (object differs OR polarity differs)) per entity
# is in the trailing comment; the total, 12, is asserted against the graph run below.
ENTITIES = {
    "dispatch-router": ("Dispatch Router", "system", [          # 1: (1,4). (0,1),(2,3) CONTRADICTS; (0,4) Conflict k-3
        ("routing_timeout", "10 seconds", A), ("routing_timeout", "4 seconds", A),
        ("timeout_fallback", "manual dispatch", A), ("timeout_fallback", "manual dispatch", D),
        ("routing_timeout", "10 seconds", A), ("assignment_push_latency", "30 seconds", A)]),
    "reefer-excursion-limit": ("Reefer Excursion Limit", "policy", [  # 2: (0,1),(0,2)
        ("excursion_limit", "30 minutes", A), ("excursion_limit", "15 minutes", A),
        ("excursion_limit", "15 minutes", A), ("excursion_threshold", "8 degrees C", A),
        ("applies_to_cargo", "all reefer loads", A)]),
    "carrier-billing": ("Carrier Billing", "system", [          # 3: (0,1),(1,2),(3,4); (0,2) equal after norm
        ("dispute_window", "30 days from delivery", A), ("dispute_window", "45 days from invoice date", A),
        ("dispute_window", "30 Days  from delivery", A), ("auto_approve_after_window", "true", A),
        ("auto_approve_after_window", "true", D)]),
    "warehouse-wms": ("Warehouse WMS", "system", [              # 0
        ("count_task_time", "22:00", A), ("count_task_time", "22:00", A),
        ("wave_release_time", "06:00", A), ("paper_counts_reconciled", "true", D)]),
    "driver-hours-limit": ("Driver Hours Limit", "policy", [    # 2: (0,1),(0,3)
        ("max_driving_hours", "11 hours", A), ("max_driving_hours", "10 hours", A),
        ("driving_time_source", "Fleet Telematics", A), ("max_driving_hours", "10 hours", A)]),
    "customs-gateway": ("Customs Gateway", "system", [          # 1: (0,1) polarity
        ("auto_filing", "24 hours before arrival", A), ("auto_filing", "24 hours before arrival", D),
        ("rejected_filing_retry", "once after 15 minutes", A)]),
    "a-class-cycle-count": ("A-Class Cycle Count", "process", [  # 1: (0,1)
        ("cycle_count_frequency", "nightly", A), ("cycle_count_frequency", "weekly", A),
        ("recount_threshold", "2 percent", A)]),
    "on-time-delivery-rate": ("On-Time Delivery Rate", "metric", [  # 0
        ("target", "95 percent", A), ("target", "95 percent", A),
        ("measured_from", "delivery window close", A)]),
    "fleet-telematics": ("Fleet Telematics", "system", [        # 1
        ("gps_interval_moving", "30 seconds", A), ("gps_interval_moving", "60 seconds", A)]),
    "dock-schedule": ("Dock Schedule", "process", [             # 0
        ("late_arrival_grace", "45 minutes", A), ("slot_length", "2 hours", A)]),
    "proof-of-delivery": ("Proof of Delivery", "artifact", [    # 1: polarity
        ("signature_required", "true", A), ("signature_required", "true", D)]),
    "finance-ledger": ("Finance Ledger", "system", [            # 0
        ("period_lock_deadline", "third business day", A)]),
}
EXPECTED_PREFILTERED = 12

SYSTEMS = [("sys-dispatch-router", "Dispatch Router", 1), ("sys-warehouse-wms", "Warehouse WMS", 1),
           ("sys-cold-chain-monitor", "Cold Chain Monitor", 1), ("sys-driver-app", "Driver App", 2),
           ("sys-carrier-billing", "Carrier Billing", 2), ("sys-fleet-telematics", "Fleet Telematics", 3)]
PEOPLE = [("person-tomas-okafor", "Tomas Okafor", "Dispatch Platform Lead", "sys-dispatch-router"),
          ("person-mei-lin-hart", "Mei Lin Hart", "Warehouse Systems Lead", "sys-warehouse-wms"),
          ("person-sofia-alvarez", "Sofia Alvarez", "Mobile Engineering Lead", "sys-driver-app")]
# SUPERSEDES chain 3 deep: ADR-90 -> ADR-71 -> ADR-52 -> ADR-30 (newer -> older)
DECISIONS = [("dec-adr-30", "ADR-30", "Manual fallback on routing timeout", "superseded", T0 - 900 * 86400),
             ("dec-adr-52", "ADR-52", "Routing timeout 10s", "superseded", T0 - 600 * 86400),
             ("dec-adr-71", "ADR-71", "Retry once before fallback", "superseded", T0 - 300 * 86400),
             ("dec-adr-90", "ADR-90", "Backup solver replaces manual fallback", "accepted", T0 - 60 * 86400)]
SUPERSEDES = [("dec-adr-52", "dec-adr-30"), ("dec-adr-71", "dec-adr-52"), ("dec-adr-90", "dec-adr-71")]


def cid(entity: str, i: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"faultline/synthetic/{entity}/{i}"))


def build() -> dict:
    claims, about = [], []
    for e_id, (name, _, specs) in ENTITIES.items():
        for i, (pred, obj, pol) in enumerate(specs):
            text = f"{name}: {pred.replace('_', ' ')} is {obj}."
            claims.append({"id": cid(e_id, i), "text": text, "polarity": pol, "subject_ref": e_id,
                           "predicate": pred, "object": obj, "evidence_span": obj,
                           # deterministic spread over [0.66, 0.98]; some fall below 0.80 to exercise $floor
                           "confidence": round(0.66 + ((len(claims) * 37) % 33) / 100, 2),
                           "extracted_at": T0})
            about.append({"c": cid(e_id, i), "e": e_id})

    dr = [cid("dispatch-router", i) for i in range(6)]
    # Two real contradictions, each with a CONTRADICTS edge and a Conflict.
    contradicts = [{"a": dr[0], "b": dr[1], "confidence": 0.92, "span": "4 seconds", "method": "synthetic"},
                   {"a": dr[2], "b": dr[3], "confidence": 0.88, "span": "manual dispatch", "method": "synthetic"}]
    conflicts = [{"id": "k-1", "status": "resolved", "kind": "superseded", "br": 0.0, "found": T0 - 86400,
                  "a": dr[0], "b": dr[1]},
                 {"id": "k-2", "status": "open", "kind": "direct", "br": 0.0, "found": T0, "a": dr[2], "b": dr[3]},
                 # Raised and dismissed with no CONTRADICTS edge: only the "Conflict involving both"
                 # clause of §7.1 can exclude this pair.
                 {"id": "k-3", "status": "dismissed", "kind": "direct", "br": 0.0, "found": T0, "a": dr[0], "b": dr[4]}]

    docs = [{"id": f"doc-{i:04d}", "title": f"Synthetic doc {i}", "path": f"synthetic/doc-{i}.md",
             "kind": ("runbook", "wiki", "spec", "readme")[i % 4], "updated_at": T0 - i * 86400}
            for i in range(8)]
    # dr[1] is asserted by a Message, not a Document (v3: ASSERTS accepts Document|Message|Ticket).
    asserts = [{"d": docs[i % len(docs)]["id"], "c": c["id"]} for i, c in enumerate(claims) if c["id"] != dr[1]]
    governs = [{"d": "doc-0000", "s": "sys-dispatch-router"}, {"d": "doc-0000", "s": "sys-driver-app"},
               {"d": "doc-0001", "s": "sys-dispatch-router"}, {"d": "doc-0002", "s": "sys-warehouse-wms"},
               {"d": "doc-0002", "s": "sys-cold-chain-monitor"},
               {"d": "doc-0003", "s": "sys-cold-chain-monitor"}, {"d": "doc-0003", "s": "sys-fleet-telematics"},
               {"d": "doc-0005", "s": "sys-carrier-billing"}]
    cites = [{"d": "doc-0000", "dec": "dec-adr-30"}, {"d": "doc-0001", "dec": "dec-adr-90"},
             {"d": "doc-0002", "dec": "dec-adr-52"}]
    return dict(claims=claims, about=about, contradicts=contradicts, conflicts=conflicts, docs=docs,
                asserts=asserts, governs=governs, cites=cites, dr=dr)


def load(g, data: dict) -> None:
    q = g.query
    q("UNWIND $rows AS r CREATE (:Entity {id: r[0], name: r[1], type: r[2]})",
      {"rows": [[e, n, t] for e, (n, t, _) in ENTITIES.items()]})
    q("UNWIND $rows AS r CREATE (:Claim {id: r.id, text: r.text, polarity: r.polarity, "
      "subject_ref: r.subject_ref, predicate: r.predicate, object: r.object, "
      "evidence_span: r.evidence_span, confidence: r.confidence, extracted_at: r.extracted_at})",
      {"rows": data["claims"]})
    q("UNWIND $rows AS r MATCH (c:Claim {id: r.c}), (e:Entity {id: r.e}) CREATE (c)-[:ABOUT]->(e)",
      {"rows": data["about"]})
    q("UNWIND $rows AS r CREATE (:Document {id: r.id, title: r.title, path: r.path, kind: r.kind, "
      "updated_at: r.updated_at})", {"rows": data["docs"]})
    q("UNWIND $rows AS r MATCH (d:Document {id: r.d}), (c:Claim {id: r.c}) CREATE (d)-[:ASSERTS]->(c)",
      {"rows": data["asserts"]})
    q("UNWIND $rows AS r CREATE (:System {id: r[0], name: r[1], tier: r[2]})",
      {"rows": [list(s) for s in SYSTEMS]})
    q("UNWIND $rows AS r MATCH (d:Document {id: r.d}), (s:System {id: r.s}) CREATE (d)-[:GOVERNS]->(s)",
      {"rows": data["governs"]})
    q("UNWIND $rows AS r MATCH (s:System {id: r[3]}) "
      "CREATE (:Person {id: r[0], name: r[1], role: r[2], active: true})-[:OWNS]->(s)",
      {"rows": [list(p) for p in PEOPLE]})
    q("UNWIND $rows AS r CREATE (:Decision {id: r[0], ref: r[1], title: r[2], status: r[3], decided_at: r[4]})",
      {"rows": [list(d) for d in DECISIONS]})
    q("UNWIND $rows AS r MATCH (n:Decision {id: r[0]}), (o:Decision {id: r[1]}) CREATE (n)-[:SUPERSEDES]->(o)",
      {"rows": [list(s) for s in SUPERSEDES]})
    q("UNWIND $rows AS r MATCH (d:Document {id: r.d}), (x:Decision {id: r.dec}) CREATE (d)-[:CITES]->(x)",
      {"rows": data["cites"]})
    q("UNWIND $rows AS r MATCH (a:Claim {id: r.a}), (b:Claim {id: r.b}) "
      "CREATE (a)-[:CONTRADICTS {confidence: r.confidence, evidence_span: r.span, method: r.method}]->(b)",
      {"rows": data["contradicts"]})
    q("UNWIND $rows AS r MATCH (a:Claim {id: r.a}), (b:Claim {id: r.b}) "
      "CREATE (k:Conflict {id: r.id, blast_radius: r.br, status: r.status, kind: r.kind, found_at: r.found}) "
      "CREATE (k)-[:INVOLVES {side: 'a'}]->(a), (k)-[:INVOLVES {side: 'b'}]->(b)",
      {"rows": data["conflicts"]})
    q("MATCH (k:Conflict {id: 'k-1'}), (w:Claim {id: $w}) "
      "CREATE (k)-[:RESOLVED_AS {rationale: 'ADR-90 is current', resolved_at: $t, resolved_by: 'person-tomas-okafor'}]->(w)",
      {"w": data["dr"][1], "t": T0})
    q("MATCH (c:Claim {id: $c}) CREATE (:Message {id: 'msg-1', channel: '#dispatch-oncall', "
      "text: 'router timeout is 4 seconds now, backup solver retries', sent_at: $t})-[:ASSERTS]->(c)",
      {"c": data["dr"][1], "t": T0})
    q("MATCH (c:Claim {id: $c}) CREATE (c)-[:DERIVED_FROM]->(:Ticket {id: 'tkt-1', ref: 'OPS-118', "
      "title: 'Manual dispatch fallback removed', text: 'Fallback to manual dispatch is no longer used.', "
      "state: 'closed', closed_at: $t})", {"c": data["dr"][3], "t": T0})


def oracle(data: dict, floor: float) -> tuple[set, set]:
    """Independent brute force for stage 2 (§7.1) and stage 3 (§6), in pure Python."""
    by_id = {c["id"]: c for c in data["claims"]}
    by_entity: dict[str, list[str]] = {}
    for r in data["about"]:
        by_entity.setdefault(r["e"], []).append(r["c"])
    judged = {frozenset((r["a"], r["b"])) for r in data["contradicts"]}
    in_conflict = {frozenset((k["a"], k["b"])) for k in data["conflicts"]}
    stage2 = {(a, b) for ids in by_entity.values() for a, b in combinations(sorted(ids), 2)
              if by_id[a]["confidence"] >= floor and by_id[b]["confidence"] >= floor
              and frozenset((a, b)) not in judged | in_conflict}
    stage3 = set()
    for a, b in stage2:
        x, y = by_id[a], by_id[b]
        if x["predicate"] == y["predicate"] and (
                norm(x["object"]) != norm(y["object"]) or x["polarity"] != y["polarity"]):
            stage3.add((a, b))
    return stage2, stage3


def funnel(g, floor: float) -> tuple[int, list, list]:
    stage2 = candidate_collapse(g, floor)
    return naive_pair_count(g), stage2, prefilter(stage2)


def main() -> int:
    g = get_graph(TENANT)
    try:
        g.delete()
    except Exception:
        pass  # graph did not exist yet
    g = get_graph(TENANT)
    apply_schema(TENANT)
    data = build()
    load(g, data)

    n = len(data["claims"])
    naive, s2, s3 = funnel(g, 0.65)
    shared = sum(len(specs) * (len(specs) - 1) // 2 for _, _, specs in ENTITIES.values())

    print(f"graph   {g.name}   claims {n}   entities {len(ENTITIES)}   floor 0.65\n")
    print(f"stage 1  all pairs            {naive:>5}   n*(n-1)/2 = {n}*{n - 1}/2, counted, never enumerated")
    print(f"stage 2  graph collapse       {len(s2):>5}   {shared} shared-Entity pairs - 2 CONTRADICTS"
          f" - 1 in a Conflict (k-3)")
    print(f"stage 3  prefilter            {len(s3):>5}   shared predicate AND (object differs OR polarity differs)")
    print(f"stage 4  LLM judgement     <= {len(s3):>5}   upper bound; Adjudicator not built, 0 model calls made")
    print(f"\n         {naive} -> {len(s2)} is {naive / len(s2):.1f}x;  {naive} -> {len(s3)} is {naive / len(s3):.1f}x\n")

    ok = len(s3) == EXPECTED_PREFILTERED
    print(f"check stage 3 == hand count {EXPECTED_PREFILTERED}: {'MATCH' if ok else 'MISMATCH'}")
    for floor in (0.65, 0.80):
        _, g2, g3 = funnel(g, floor)
        e2, e3 = oracle(data, floor)
        got2, got3 = {(r["a_id"], r["b_id"]) for r in g2}, {(r["a_id"], r["b_id"]) for r in g3}
        match = got2 == e2 and got3 == e3 and len(g2) == len(got2)
        ok &= match
        print(f"check floor={floor}: stage2 falkor {len(got2)} / oracle {len(e2)}, "
              f"stage3 falkor {len(got3)} / oracle {len(e3)} -> {'MATCH' if match else 'MISMATCH'}")

    dr = data["dr"]
    cross = {tuple(sorted(p)) for p in [(dr[0], dr[2]), (dr[0], dr[3]), (dr[1], dr[2]), (dr[1], dr[3])]}
    got = {(r["a_id"], r["b_id"]) for r in s2}
    included = cross <= got
    ok &= included and tuple(sorted((dr[0], dr[4]))) not in got
    print(f"check pairs whose sides sit in DIFFERENT conflicts are kept: {'yes' if included else 'NO'}")
    print(f"check pair in dismissed Conflict k-3 (no CONTRADICTS) is excluded: "
          f"{'yes' if tuple(sorted((dr[0], dr[4]))) not in got else 'NO'}")

    print("\n7.2 current_claim(dec-adr-30):", current_claim(g, "dec-adr-30"))
    print("7.2 current_claim(dec-adr-90):", current_claim(g, "dec-adr-90"))
    br = blast_radius(g, next(r["c"] for r in data["asserts"] if r["d"] == "doc-0002"))
    print("7.3 blast_radius(claim in doc-0002, two tier-1 systems):", br)
    ok &= br["tier_weight"] == 6
    print("7.3 conflict roll-up k-2 = max(side a, side b):", conflict_blast_radius(g, dr[2], dr[3]))
    msg_br = blast_radius(g, dr[1])
    print("7.3 blast_radius(message-asserted claim, untyped src):", msg_br["score"])
    ok &= msg_br["doc_count"] == 1 and msg_br["score"] == 1.0
    pre = precedent(g, "dispatch-router")
    ok &= len(pre) == 1
    print("7.4 precedent(dispatch-router):", pre)
    path = traversal_path(g, "k-2")
    print(f"7.5 traversal_path(k-2): {len(path)} rows; keys {list(path[0]) if path else []}")
    print("\nALL CHECKS PASSED" if ok else "\nCHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
