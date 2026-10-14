"""Constraints and indexes from CONTRACT §5.3 (v3), applied idempotently.

Uniqueness goes through the native GRAPH.CONSTRAINT CREATE command. A unique constraint
needs an exact-match range index on the property first; those are plain Cypher. Creation
is asynchronous, so apply_schema polls until every constraint is OPERATIONAL. The contract
says to poll GRAPH.CONSTRAINT LIST; FalkorDB has no such subcommand, so the poll uses
CALL db.constraints(), which reports the same status.

Run:  python -m graph.schema [tenant_id]
"""

from __future__ import annotations

import sys
import time

from falkordb import Graph
from redis.exceptions import ResponseError

from graph.connection import DEFAULT_TENANT, get_graph

UNIQUE_ID_LABELS = ("Claim", "Entity", "Document", "Decision", "Person", "System", "Conflict")

INDEXES = (
    "CREATE INDEX FOR (c:Claim)    ON (c.confidence)",
    "CREATE INDEX FOR (c:Claim)    ON (c.predicate)",
    "CREATE INDEX FOR (e:Entity)   ON (e.name)",
    "CREATE INDEX FOR (k:Conflict) ON (k.status)",
    "CREATE INDEX FOR (k:Conflict) ON (k.blast_radius)",
)


def _create_index(g: Graph, cypher: str) -> bool:
    """Returns True if created, False if it already existed."""
    try:
        g.query(cypher)
        return True
    except ResponseError as e:
        if "already indexed" in str(e):
            return False
        raise


def _existing_unique_constraints(g: Graph) -> set[str]:
    rows = g.ro_query("CALL db.constraints() YIELD type, label, properties, entitytype").result_set
    return {label for type_, label, props, entity in rows
            if type_ == "UNIQUE" and entity == "NODE" and props == ["id"]}


def apply_schema(tenant_id: str = DEFAULT_TENANT, timeout_s: float = 30.0) -> dict:
    g = get_graph(tenant_id)
    created_idx, created_con = [], []

    for label in UNIQUE_ID_LABELS:
        if _create_index(g, f"CREATE INDEX FOR (n:{label}) ON (n.id)"):
            created_idx.append(f"{label}.id")
    for cypher in INDEXES:
        if _create_index(g, cypher):
            created_idx.append(cypher)

    existing = _existing_unique_constraints(g)
    for label in UNIQUE_ID_LABELS:
        if label not in existing:
            g.execute_command("GRAPH.CONSTRAINT", "CREATE", g.name,
                              "UNIQUE", "NODE", label, "PROPERTIES", 1, "id")
            created_con.append(label)

    deadline = time.monotonic() + timeout_s
    while True:
        pending = [c["label"] for c in constraint_status(tenant_id) if c["status"] != "OPERATIONAL"]
        if not pending:
            break
        if time.monotonic() > deadline:
            raise TimeoutError(f"constraints not OPERATIONAL after {timeout_s}s: {pending}")
        time.sleep(0.1)

    return {"graph": g.name, "indexes_created": created_idx, "constraints_created": created_con}


def constraint_status(tenant_id: str = DEFAULT_TENANT) -> list[dict]:
    rows = get_graph(tenant_id).ro_query(
        "CALL db.constraints() YIELD type, label, properties, entitytype, status").result_set
    return [dict(zip(("type", "label", "properties", "entitytype", "status"), r)) for r in rows]


if __name__ == "__main__":
    print(apply_schema(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TENANT))
