"""MCP tools (CONTRACT §8), served by FastMCP from the API process at /mcp.

Every tool returns JSON. Errors return {"error": "<message>"} as a normal result, so the
calling agent handles them rather than the transport. Each tool is a thin wrapper over the
same Cypher the API and the Adjudicator use; there is no second implementation.
"""

from __future__ import annotations

import functools
from typing import Any

from fastmcp import FastMCP

from agent import adjudicator
from graph.connection import get_graph
from graph.prefilter import prefilter
from graph.queries import blast_radius as _blast_radius
from graph.queries import candidate_collapse, naive_pair_count, precedent, rows

TENANT = "northwind"
mcp = FastMCP("faultline")


def _safe(fn):
    @functools.wraps(fn)  # keeps the signature FastMCP builds the tool schema from
    def wrapped(*args, **kwargs) -> dict[str, Any]:
        try:
            return fn(*args, **kwargs)
        except Exception as e:  # §8: errors are results, not transport failures
            return {"error": f"{type(e).__name__}: {e}"}

    return wrapped


@mcp.tool
@_safe
def find_candidates(entity_id: str | None = None, floor: float = 0.65, limit: int = 200) -> dict:
    """Stage-3 claim pairs not yet judged (§7.1 collapse, then the prefilter), optionally for one entity."""
    g = get_graph(TENANT)
    s2 = candidate_collapse(g, floor)
    s3 = prefilter(s2)
    pairs = [p for p in s3 if entity_id in (None, p["entity_id"])][:limit]
    return {"pairs": pairs, "naive_pair_count": naive_pair_count(g),
            "collapsed_pair_count": len(s2), "prefiltered_pair_count": len(s3)}


@mcp.tool
@_safe
def judge_pair(a_id: str, b_id: str) -> dict:
    """Ask the judge model whether two claims contradict. Cached; writes nothing."""
    g = get_graph(TENANT)
    a, b = adjudicator._claim(g, a_id), adjudicator._claim(g, b_id)
    entity = rows(g, "MATCH (:Claim {id: $id})-[:ABOUT]->(e:Entity) RETURN e.name AS name", {"id": a_id})
    verdict, _ = adjudicator.judge(a, b, entity[0]["name"] if entity else "")
    return {k: verdict[k] for k in ("verdict", "confidence", "evidence_span", "reasoning") if k in verdict}


@mcp.tool
@_safe
def blast_radius(claim_id: str) -> dict:
    """§7.3: what sits downstream of a claim, scored exactly as the contract writes it."""
    g = get_graph(TENANT)
    if not rows(g, "MATCH (c:Claim {id: $id}) RETURN c.id AS id", {"id": claim_id}):
        return {"error": f"claim {claim_id!r} not found"}
    return _blast_radius(g, claim_id)


CURRENT = """
MATCH (e:Entity {id: $entity_id})<-[:ABOUT]-(:Claim)<-[:ASSERTS]-(:Document)-[:CITES]->(d:Decision)
OPTIONAL MATCH (live:Decision)-[:SUPERSEDES*0..10]->(d)
WHERE NOT (:Decision)-[:SUPERSEDES]->(live)
RETURN DISTINCT live.id AS id, live.ref AS ref, live.title AS title, live.decided_at AS decided_at
"""

SUPERSEDED_BY = """
MATCH (live:Decision {id: $id})-[:SUPERSEDES*1..10]->(old:Decision)
RETURN old.id AS id, old.ref AS ref, old.title AS title, old.decided_at AS decided_at
ORDER BY old.decided_at DESC
"""


@mcp.tool
@_safe
def current_claim(entity_id: str) -> dict:
    """§7.2 by traversal: the decision nothing supersedes, reached from the decisions cited about this entity."""
    g = get_graph(TENANT)
    heads = [h for h in rows(g, CURRENT, {"entity_id": entity_id}) if h["id"]]
    if not heads:
        return {"current_decision": None, "chain_depth": 0, "superseded": []}
    head = max(heads, key=lambda h: h["decided_at"] or 0)
    older = rows(g, SUPERSEDED_BY, {"id": head["id"]})
    return {"current_decision": head, "chain_depth": len(older),
            "superseded": [{"id": o["id"], "ref": o["ref"], "title": o["title"]} for o in older]}


@mcp.tool
@_safe
def precedent_for(a_id: str, b_id: str) -> dict:
    """§7.4: has a conflict about this entity already been settled, and for which claim?"""
    g = get_graph(TENANT)
    ent = rows(g, "MATCH (:Claim {id: $id})-[:ABOUT]->(e:Entity) RETURN e.id AS id", {"id": a_id})
    found = precedent(g, ent[0]["id"]) if ent else []
    hit = next((r for r in found if r["winner_id"] in (a_id, b_id)), found[0] if found else None)
    if not hit:
        return {"found": False, "conflict_id": None, "winner_id": None, "winner_text": None, "settled_at": None}
    return {"found": True, **hit}


@mcp.tool
@_safe
def route_owner(conflict_id: str) -> dict:
    """Who should fix it: the owner of the most critical system downstream of either side, with the path."""
    from api import service

    c = service.get_conflict(conflict_id, TENANT)
    owner = c["conflict"]["owner"]
    path = [{"id": n["id"], "label": n["label"], "type": n["type"]} for n in c["path"]["nodes"]
            if n["type"] in ("claim", "document", "system", "person")]
    reason = (f"{owner['name']} owns the most critical system governed by a document asserting either claim."
              if owner else "No Person OWNS a system governed by either side's documents.")
    return {"owner": owner, "path": path, "reason": reason}
