"""Graph-backed implementations of CONTRACT §9. Every response is built from FalkorDB.

Shapes match fixtures/*.json exactly; the fixtures are the contract's worked examples.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Any

from falkordb import Graph

from agent import llm
from agent.adjudicator import FLOOR, classify, judge_cache_hit, sources_of
from graph.connection import get_graph
from graph.prefilter import prefilter
from graph.queries import blast_radius, naive_pair_count, rows, shared_entity_pairs, traversal_path

PATH_CAP = 40  # rule 3: the UI renders a traversal path, never the whole graph


class NotFound(Exception):
    pass


class Invalid(Exception):
    pass


class Conflicting(Exception):
    """The request is valid but the record is in the wrong state for it (HTTP 409)."""


# ------------------------------------------------------------------ Conflict
CONFLICTS = """
MATCH (k:Conflict)
WHERE $status IS NULL OR k.status = $status
RETURN k.id AS id, k.kind AS kind, k.status AS status, k.blast_radius AS blast_radius, k.found_at AS found_at,
       k.dismissed_by AS dismissed_by, k.dismiss_rationale AS dismiss_rationale, k.dismissed_at AS dismissed_at
ORDER BY k.blast_radius DESC, k.id
LIMIT $limit
"""

CONFLICT = """
MATCH (k:Conflict {id: $id})
RETURN k.id AS id, k.kind AS kind, k.status AS status, k.blast_radius AS blast_radius, k.found_at AS found_at,
       k.dismissed_by AS dismissed_by, k.dismiss_rationale AS dismiss_rationale, k.dismissed_at AS dismissed_at
"""

SIDES = """
MATCH (k:Conflict {id: $id})-[i:INVOLVES]->(c:Claim)
OPTIONAL MATCH (c)-[:ABOUT]->(e:Entity)
OPTIONAL MATCH (k)-[r:RESOLVED_AS]->(w:Claim)
RETURN i.side AS side, c.id AS id, c.text AS text, c.confidence AS confidence,
       c.evidence_span AS evidence_span, c.predicate AS predicate, c.object AS object,
       e.id AS entity_id, e.name AS entity_name, e.type AS entity_type, w.id AS winner_id,
       r.rationale AS rationale, r.resolved_at AS resolved_at, r.resolved_by AS resolved_by
ORDER BY side
"""

JUDGEMENT = """
MATCH (a:Claim)-[r:CONTRADICTS]-(b:Claim)
WHERE a.id = $a AND b.id = $b
RETURN r.method AS method, r.confidence AS confidence, r.evidence_span AS evidence_span
LIMIT 1
"""

IMPACT = """
MATCH (c:Claim) WHERE c.id IN $ids
OPTIONAL MATCH (src)-[:ASSERTS]->(c)
OPTIONAL MATCH (src)-[:GOVERNS]->(s:System)
OPTIONAL MATCH (p:Person)-[:OWNS]->(s)
RETURN count(DISTINCT src) AS doc_count,
       collect(DISTINCT {id: s.id, name: s.name, tier: s.tier}) AS systems,
       collect(DISTINCT {id: p.id, name: p.name, role: p.role, tier: s.tier}) AS owners
"""


def _sides(g: Graph, conflict_id: str) -> list[dict]:
    sides = rows(g, SIDES, {"id": conflict_id})
    if len(sides) != 2:
        raise Invalid(f"conflict {conflict_id} involves {len(sides)} claims, expected 2")
    return sides


def _states(g: Graph, k: dict, sides: list[dict]) -> tuple[dict[str, str], dict[str, list[dict]]]:
    src = {s["side"]: sources_of(g, s["id"]) for s in sides}
    winner = sides[0]["winner_id"]
    if k["status"] == "resolved" and winner:
        return {s["side"]: ("live" if s["id"] == winner else "superseded") for s in sides}, src
    _, states = classify(g, src["a"], src["b"])
    return states, src


def _source(srcs: list[dict]) -> dict:
    """The asserting source shown for a claim: a Document when there is one."""
    if not srcs:
        return {"doc_id": "", "title": "", "path": "", "updated_at": 0}
    s = sorted(srcs, key=lambda x: (x["label"] != "Document", x["id"]))[0]
    return {"doc_id": s["id"], "title": s["title"] or s["id"], "path": s["path"] or "", "updated_at": int(s["at"] or 0)}


def _impact(g: Graph, claim_ids: list[str]) -> tuple[dict, dict | None]:
    r = rows(g, IMPACT, {"ids": claim_ids})[0]
    systems = sorted((s for s in r["systems"] if s["id"]), key=lambda s: (s["tier"], s["name"]))
    owners = sorted((o for o in r["owners"] if o["id"]), key=lambda o: (o["tier"], o["name"]))
    # Route to whoever owns the most critical system downstream of either side.
    owner = {"id": owners[0]["id"], "name": owners[0]["name"], "role": owners[0]["role"]} if owners else None
    impact = {"doc_count": r["doc_count"], "system_count": len(systems), "systems": [s["name"] for s in systems]}
    return impact, owner


def build_conflict(g: Graph, k: dict) -> dict:
    sides = _sides(g, k["id"])
    states, src = _states(g, k, sides)
    impact, owner = _impact(g, [s["id"] for s in sides])
    first = sides[0]
    judged = rows(g, JUDGEMENT, {"a": sides[0]["id"], "b": sides[1]["id"]})
    resolution = None
    if first["winner_id"]:
        resolution = {"winner_claim_id": first["winner_id"], "rationale": first["rationale"],
                      "resolved_at": int(first["resolved_at"] or 0), "resolved_by": first["resolved_by"]}
    return {
        "id": k["id"],
        "kind": k["kind"],
        "status": k["status"],
        "blast_radius": float(k["blast_radius"]),
        "found_at": int(k["found_at"]),
        "entity": {"id": first["entity_id"], "name": first["entity_name"], "type": first["entity_type"]},
        "claims": [{
            "side": s["side"],
            "id": s["id"],
            "text": s["text"],
            "confidence": float(s["confidence"]),
            "evidence_span": s["evidence_span"],
            "state": states[s["side"]],
            "source": _source(src[s["side"]]),
        } for s in sides],
        "impact": impact,
        "owner": owner,
        # Optional in CONTRACT §9 v5: the judgement behind CONTRADICTS, and the RESOLVED_AS record.
        "judgement": judged[0] if judged else None,
        "resolution": resolution,
        # v7: who dismissed it and why, null unless status is "dismissed"
        "dismissal": ({"rationale": k.get("dismiss_rationale") or "", "dismissed_by": k.get("dismissed_by") or "",
                       "dismissed_at": int(k["dismissed_at"])}
                      if k["status"] == "dismissed" and k.get("dismissed_at") else None),
    }


def list_conflicts(status: str | None, limit: int, tenant: str = "northwind") -> dict:
    g = get_graph(tenant)
    status = None if status in (None, "", "all") else status
    ks = rows(g, CONFLICTS, {"status": status, "limit": limit})
    total = rows(g, "MATCH (k:Conflict) WHERE $status IS NULL OR k.status = $status RETURN count(k) AS n",
                 {"status": status})[0]["n"]
    return {"conflicts": [build_conflict(g, k) for k in ks], "total": total, "stats": stats(tenant)}


def get_conflict(conflict_id: str, tenant: str = "northwind") -> dict:
    g = get_graph(tenant)
    found = rows(g, CONFLICT, {"id": conflict_id})
    if not found:
        raise NotFound(f"conflict {conflict_id!r} not found")
    conflict = build_conflict(g, found[0])
    return {"conflict": conflict, "path": build_path(g, conflict), "precedent": precedent_for(g, conflict)}


# §7.4's question, with the RESOLVED_AS date: what has already been settled about this Entity?
PRECEDENT = """
MATCH (k:Conflict {status: 'resolved'})-[:INVOLVES]->(:Claim)-[:ABOUT]->(e:Entity {id: $entity_id})
MATCH (k)-[r:RESOLVED_AS]->(winner:Claim)
RETURN DISTINCT k.id AS conflict_id, winner.id AS winner_id, winner.text AS winner_text,
       r.resolved_at AS settled_at
ORDER BY settled_at DESC
LIMIT 5
"""


def precedent_for(g: Graph, conflict: dict) -> dict:
    """CONTRACT §9 v7 Precedent: settled conflicts about the same Entity, newest first."""
    settled = [r for r in rows(g, PRECEDENT, {"entity_id": conflict["entity"]["id"]})
               if r["conflict_id"] != conflict["id"]]
    for r in settled:
        r["settled_at"] = int(r["settled_at"] or 0)
    return {"found": bool(settled), "settled": settled}


# ------------------------------------------------------------------ GraphPath
SOURCE_NODES = """
MATCH (s)-[:ASSERTS]->(c:Claim) WHERE c.id IN $ids
RETURN DISTINCT labels(s)[0] AS label, s.id AS id, c.id AS claim,
       coalesce(s.title, s.channel, s.ref) AS title,
       coalesce(s.updated_at, s.sent_at, s.closed_at) AS at
"""

DECISION_EDGES = """
MATCH (x:Decision)-[:SUPERSEDES]->(y:Decision)
WHERE x.id IN $ids AND y.id IN $ids
RETURN x.id AS source, y.id AS target
"""

CONTRADICTS_EDGES = """
MATCH (a:Claim)-[:CONTRADICTS]->(b:Claim)
WHERE a.id IN $ids AND b.id IN $ids
RETURN a.id AS source, b.id AS target
"""

OWNED = """
MATCH (p:Person {id: $person})-[:OWNS]->(s:System)
WHERE s.id IN $systems
RETURN s.id AS system
"""


def _claim_label(c: dict) -> str:
    return f"{c['predicate'].replace('_', ' ')}: {c['object']}"


def build_path(g: Graph, conflict: dict) -> dict:
    """§7.5 plus the sources §7.5 cannot see (claims asserted by a Message or Ticket), the
    claims' Entity, the SUPERSEDES edges between the decisions it returns, and the routed owner."""
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    seen_edges: set[tuple] = set()

    def node(id_: str, label: str, type_: str, state: str | None = None, at: int | None = None) -> None:
        if id_ and id_ not in nodes:
            nodes[id_] = {"id": id_, "label": label, "type": type_, **({"state": state} if state else {}),
                          **({"at": int(at)} if at else {})}

    def edge(source: str, target: str, type_: str) -> None:
        key = (source, target, type_)
        if source in nodes and target in nodes and key not in seen_edges:
            seen_edges.add(key)
            edges.append({"source": source, "target": target, "type": type_})

    sides = {s["id"]: s for s in rows(g, SIDES, {"id": conflict["id"]})}
    claim_ids = [c["id"] for c in conflict["claims"]]
    for c in conflict["claims"]:
        # A claim is dated by the source that asserts it (§9 v5: GraphNode.at).
        node(c["id"], _claim_label(sides[c["id"]]), "claim", c["state"], c["source"]["updated_at"] or None)
    ent = conflict["entity"]
    node(ent["id"], ent["name"], "entity")
    for cid in claim_ids:
        edge(cid, ent["id"], "ABOUT")
    for e in rows(g, CONTRADICTS_EDGES, {"ids": claim_ids}):
        edge(e["source"], e["target"], "CONTRADICTS")

    for s in rows(g, SOURCE_NODES, {"ids": claim_ids}):
        node(s["id"], s["title"] or s["id"], s["label"].lower(), at=s["at"])
        edge(s["id"], s["claim"], "ASSERTS")

    decisions: set[str] = set()
    for r in traversal_path(g, conflict["id"]):
        d, s, dec, sup, src = r.get("d"), r.get("s"), r.get("dec"), r.get("sup"), r.get("src")
        for x in (dec, sup):
            if x:
                decisions.add(x["id"])
                ref, title = x.get("ref", x["id"]), x.get("title", "")
                # Northwind titles already start with the ref ("ADR-41: ..."); never print it twice.
                label = title if title.startswith(ref) else f"{ref}: {title}".rstrip(": ")
                node(x["id"], label, "decision",
                     {"superseded": "superseded", "accepted": "live"}.get(x.get("status", "")), x.get("decided_at"))
        if s:
            node(s["id"], s.get("name", s["id"]), "system")
        if d and s:
            edge(d["id"], s["id"], "GOVERNS")
        if d and dec:
            edge(d["id"], dec["id"], "CITES")
        if src and r.get("c"):
            node(src["id"], src.get("channel") or src.get("ref") or src["id"], src["labels"][0].lower(),
                 at=src.get("sent_at") or src.get("closed_at"))
            edge(r["c"]["id"], src["id"], "DERIVED_FROM")
    for e in rows(g, DECISION_EDGES, {"ids": sorted(decisions)}):
        edge(e["source"], e["target"], "SUPERSEDES")

    owner = conflict["owner"]
    if owner:
        node(owner["id"], owner["name"], "person")
        systems = [n["id"] for n in nodes.values() if n["type"] == "system"]
        for r in rows(g, OWNED, {"person": owner["id"], "systems": systems}):
            edge(owner["id"], r["system"], "OWNS")

    kept = list(nodes.values())[:PATH_CAP]
    ids = {n["id"] for n in kept}
    return {"nodes": kept, "edges": [e for e in edges if e["source"] in ids and e["target"] in ids]}


# ------------------------------------------------------------------ Stats
_stats_cache: dict[str, tuple[float, dict]] = {}
STATS_TTL_S = 10.0


def stats(tenant: str = "northwind") -> dict:
    """The four funnel numbers, measured on the graph. Cached for a few seconds because
    /conflicts embeds it and the queue polls both."""
    hit = _stats_cache.get(tenant)
    if hit and time.monotonic() - hit[0] < STATS_TTL_S:
        return hit[1]
    g = get_graph(tenant)
    count = lambda q: rows(g, q)[0]["n"]  # noqa: E731
    s2 = shared_entity_pairs(g, FLOOR)
    s3 = prefilter(s2)
    judged = sum(1 for p in s3 if judge_cache_hit(p["a_text"], p["b_text"], p["entity"]))
    out = {
        "claims": count("MATCH (c:Claim) RETURN count(c) AS n"),
        "documents": count("MATCH (d:Document) RETURN count(d) AS n"),
        "entities": count("MATCH (e:Entity) RETURN count(e) AS n"),
        "naive_pair_count": naive_pair_count(g),
        "collapsed_pair_count": len(s2),
        "prefiltered_pair_count": len(s3),
        "judged_pair_count": judged,
        "conflicts_open": count("MATCH (k:Conflict {status: 'open'}) RETURN count(k) AS n"),
        "conflicts_resolved": count("MATCH (k:Conflict {status: 'resolved'}) RETURN count(k) AS n"),
    }
    _stats_cache[tenant] = (time.monotonic(), out)
    return out


# ------------------------------------------------------------------ Reconciler
RESOLVE = """
MATCH (k:Conflict {id: $id}), (w:Claim {id: $winner})
MERGE (k)-[r:RESOLVED_AS]->(w)
SET r.rationale = $rationale, r.resolved_at = $at, r.resolved_by = $by,
    k.status = 'resolved', k.blast_radius = $radius
"""


def dismiss(conflict_id: str, rationale: str, dismissed_by: str, tenant: str = "northwind") -> dict:
    """An open conflict judged not to be one. The reason, who and when are kept on the Conflict
    (§5 v7), and the Adjudicator never re-flags a pair that a Conflict already involves."""
    g = get_graph(tenant)
    found = rows(g, CONFLICT, {"id": conflict_id})
    if not found:
        raise NotFound(f"conflict {conflict_id!r} not found")
    if found[0]["status"] != "open":
        raise Conflicting(f"conflict {conflict_id!r} is {found[0]['status']}, not open")
    if not rationale.strip() or not dismissed_by.strip():
        raise Invalid("rationale and dismissed_by are both required")
    g.query("MATCH (k:Conflict {id: $id}) SET k.status = 'dismissed', k.dismissed_by = $by, "
            "k.dismiss_rationale = $rationale, k.dismissed_at = $at",
            {"id": conflict_id, "by": dismissed_by.strip(), "rationale": rationale.strip(), "at": int(time.time())})
    _stats_cache.pop(tenant, None)
    return {"ok": True, "conflict": get_conflict(conflict_id, tenant)["conflict"]}


def resolve(conflict_id: str, winner_claim_id: str, rationale: str, resolved_by: str,
            tenant: str = "northwind") -> dict:
    g = get_graph(tenant)
    if not rows(g, CONFLICT, {"id": conflict_id}):
        raise NotFound(f"conflict {conflict_id!r} not found")
    state = rows(g, CONFLICT, {"id": conflict_id})[0]["status"]
    if state != "open":
        raise Conflicting(f"conflict {conflict_id!r} is {state}, not open")
    sides = _sides(g, conflict_id)
    if winner_claim_id not in {s["id"] for s in sides}:
        raise Invalid(f"winner_claim_id {winner_claim_id!r} is not one of this conflict's two claims")
    if not rationale.strip() or not resolved_by.strip():
        raise Invalid("rationale and resolved_by are both required")
    loser = next(s["id"] for s in sides if s["id"] != winner_claim_id)
    # §7.3: after resolution a conflict scores the blast radius of the losing claim.
    g.query(RESOLVE, {"id": conflict_id, "winner": winner_claim_id, "rationale": rationale,
                      "at": int(time.time()), "by": resolved_by, "radius": blast_radius(g, loser)["score"]})
    _stats_cache.pop(tenant, None)
    return {"ok": True, "conflict": get_conflict(conflict_id, tenant)["conflict"]}


DRAFT_PROMPT = """You draft a documentation correction for an organisation whose documents contradict each other.
You are given the conflict: the claim to correct, the claim that is current, and their sources.
Write plainly. State the finding, then the evidence, then the date. No exclamation marks.
Return JSON only:
{"correction": "<the replacement sentence or paragraph for the outdated source, ready to paste>",
 "ticket_title": "<under 80 characters>",
 "ticket_body": "<what is wrong, where, what it should say, and why; under 120 words>"}"""


def draft(conflict_id: str, tenant: str = "northwind") -> dict:
    c = get_conflict(conflict_id, tenant)["conflict"]
    if c["owner"] is None:
        raise Invalid("no Person OWNS a system downstream of this conflict, so there is no one to route it to")
    by_state = {cl["state"]: cl for cl in c["claims"]}
    current = by_state.get("live")
    stale = next((cl for cl in c["claims"] if cl is not current), c["claims"][0])
    content = json.dumps({
        "kind": c["kind"], "entity": c["entity"]["name"],
        "to_correct": {"text": stale["text"], "source": stale["source"]},
        "current": ({"text": current["text"], "source": current["source"]} if current else None),
        "note": None if current else "Neither side is known to be current; the correction must ask the owner to decide.",
    }, sort_keys=True)
    r = llm.generate("judge", DRAFT_PROMPT, content, temperature=0, response_format={"type": "json_object"})
    out = json.loads(r.value)
    return {"correction": str(out.get("correction", "")), "owner": c["owner"],
            "ticket": {"title": str(out.get("ticket_title", "")), "body": str(out.get("ticket_body", ""))}}


# ------------------------------------------------------------------ Reingest
_jobs: dict[str, dict[str, Any]] = {}


def start_reingest(tenant: str = "northwind") -> str:
    """Never on the demo path (rule 4). Re-runs ingest and adjudication in a background thread."""
    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {"state": "running", "started_at": int(time.time())}

    def work() -> None:
        try:
            import subprocess
            import sys
            for cmd in (["-m", "agent.ingest", "--tenant", tenant], ["-m", "agent.adjudicator", "--tenant", tenant]):
                subprocess.run([sys.executable, *cmd], check=True)
            _jobs[job_id]["state"] = "done"
        except Exception as e:  # reported on the job, never swallowed
            _jobs[job_id].update(state="failed", error=f"{type(e).__name__}: {e}")
        _stats_cache.pop(tenant, None)

    threading.Thread(target=work, daemon=True).start()
    return job_id
