"""The five core queries from CONTRACT §7 (v4). Raw Cypher, plain-dict results.

Every function takes the tenant's Graph (graph.connection.get_graph) so the same code
runs against faultline:northwind or any other tenant graph.
"""

from __future__ import annotations

from typing import Any

from falkordb import Edge, Graph, Node, Path

# §7.1 verbatim. Verified against FalkorDB: bare pattern predicates, not EXISTS(pattern);
# a.id < b.id removes reversed duplicates AND self-pairs (the pattern binds a == b).
CANDIDATE_COLLAPSE = """
MATCH (a:Claim)-[:ABOUT]->(e:Entity)<-[:ABOUT]-(b:Claim)
WHERE a.id < b.id
  AND a.confidence >= $floor
  AND b.confidence >= $floor
  AND NOT (a)-[:CONTRADICTS]-(b)
  AND NOT (a)<-[:INVOLVES]-(:Conflict)-[:INVOLVES]->(b)
RETURN a.id AS a_id, a.text AS a_text, a.predicate AS a_pred,
       a.object AS a_obj, a.polarity AS a_pol,
       b.id AS b_id, b.text AS b_text, b.predicate AS b_pred,
       b.object AS b_obj, b.polarity AS b_pol,
       e.id AS entity_id, e.name AS entity
ORDER BY e.id
"""

CLAIM_COUNT = "MATCH (c:Claim) RETURN count(c) AS n"

# §7.2 verbatim.
CURRENT_CLAIM = """
MATCH (start:Decision {id: $decision_id})
OPTIONAL MATCH (live:Decision)-[:SUPERSEDES*1..10]->(start)
WHERE NOT (:Decision)-[:SUPERSEDES]->(live)
RETURN coalesce(live, start) AS current,
       coalesce(length(shortestPath((live)-[:SUPERSEDES*]->(start))), 0) AS chain_depth
"""

# §7.3 verbatim. src is untyped so Message- and Ticket-sourced claims count too.
# Scoring happens in Python (blast_radius below), never sum(DISTINCT ...).
BLAST_RADIUS = """
MATCH (c:Claim {id: $claim_id})
OPTIONAL MATCH (src)-[:ASSERTS]->(c)
OPTIONAL MATCH (src)-[:GOVERNS]->(s:System)
OPTIONAL MATCH (src)-[:CITES]->(dec:Decision)
OPTIONAL MATCH (p:Person)-[:OWNS]->(s)
RETURN
  count(DISTINCT src) AS doc_count,
  count(DISTINCT dec) AS citing_decisions,
  collect(DISTINCT {id: s.id, tier: s.tier}) AS systems,
  collect(DISTINCT {id: p.id, name: p.name}) AS owners
"""

# §7.4 verbatim.
PRECEDENT = """
MATCH (k:Conflict)-[:INVOLVES]->(a:Claim)-[:ABOUT]->(e:Entity)
MATCH (k)-[:RESOLVED_AS]->(winner:Claim)
WHERE e.id = $entity_id AND k.status = 'resolved'
RETURN DISTINCT k.id AS conflict_id, winner.id AS winner_id,
       winner.text AS winner_text, k.found_at AS settled_at
ORDER BY k.found_at DESC
LIMIT 5
"""

# §7.5 verbatim.
TRAVERSAL_PATH = """
MATCH (k:Conflict {id: $conflict_id})-[:INVOLVES]->(c:Claim)
OPTIONAL MATCH (d:Document)-[:ASSERTS]->(c)
OPTIONAL MATCH (d)-[:GOVERNS]->(s:System)
OPTIONAL MATCH (d)-[:CITES]->(dec:Decision)
OPTIONAL MATCH (dec)<-[:SUPERSEDES*0..3]-(sup:Decision)
OPTIONAL MATCH (c)-[:DERIVED_FROM]->(src)
RETURN c, d, s, dec, sup, src
LIMIT 40
"""


def _plain(v: Any) -> Any:
    """FalkorDB result values -> JSON-safe Python. Nodes keep their graph labels."""
    if isinstance(v, Node):
        return {"labels": list(v.labels or []), **(v.properties or {})}
    if isinstance(v, Edge):
        return {"type": v.relation, **(v.properties or {})}
    if isinstance(v, Path):
        return {"nodes": [_plain(n) for n in v.nodes()], "edges": [_plain(e) for e in v.edges()]}
    if isinstance(v, list):
        return [_plain(x) for x in v]
    if isinstance(v, dict):
        return {k: _plain(x) for k, x in v.items()}
    return v


def _rows(g: Graph, cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    res = g.ro_query(cypher, params or {})
    cols = [h[1] if isinstance(h, (list, tuple)) else h for h in res.header]
    cols = [c.decode() if isinstance(c, bytes) else c for c in cols]
    return [dict(zip(cols, (_plain(v) for v in row))) for row in res.result_set]


def candidate_collapse(g: Graph, floor: float = 0.65) -> list[dict[str, Any]]:
    """§7.1 — claim pairs sharing an Entity, not yet judged. Funnel stage 2."""
    return _rows(g, CANDIDATE_COLLAPSE, {"floor": floor})


def naive_pair_count(g: Graph) -> int:
    """Funnel stage 1: n*(n-1)/2 over every Claim in the graph. Counted, never enumerated."""
    n = _rows(g, CLAIM_COUNT)[0]["n"]
    return n * (n - 1) // 2


def current_claim(g: Graph, decision_id: str) -> dict[str, Any] | None:
    """§7.2 — the decision nothing supersedes, reached by walking SUPERSEDES from decision_id."""
    rows = _rows(g, CURRENT_CLAIM, {"decision_id": decision_id})
    return rows[0] if rows else None


def blast_radius(g: Graph, claim_id: str) -> dict[str, Any]:
    """§7.3 — counts from Cypher, score in Python exactly as the contract writes it."""
    r = _rows(g, BLAST_RADIUS, {"claim_id": claim_id})[0]
    systems = [s for s in r["systems"] if s["id"]]
    owners = [o for o in r["owners"] if o["id"]]
    tier_weight = sum(4 - s["tier"] for s in systems)
    return {
        "score": (tier_weight * 2.0) + r["doc_count"] + (r["citing_decisions"] * 1.5),
        "doc_count": r["doc_count"],
        "system_count": len(systems),
        "citing_decisions": r["citing_decisions"],
        "tier_weight": tier_weight,
        "owners": owners,
    }


def conflict_blast_radius(g: Graph, a_id: str, b_id: str) -> float:
    """§7.3 roll-up: an open Conflict scores the MAX of its two sides, never the sum."""
    return max(blast_radius(g, a_id)["score"], blast_radius(g, b_id)["score"])


def precedent(g: Graph, entity_id: str) -> list[dict[str, Any]]:
    """§7.4 — resolved conflicts about entity_id, newest first."""
    return _rows(g, PRECEDENT, {"entity_id": entity_id})


def traversal_path(g: Graph, conflict_id: str) -> list[dict[str, Any]]:
    """§7.5 — raw rows (c, d, s, dec, sup, src) behind one conflict, capped at 40."""
    return _rows(g, TRAVERSAL_PATH, {"conflict_id": conflict_id})
