"""Drop-in /health and /api/health router for Faultline (CONTRACT §9).

Body: {"ok": bool, "graph": str, "nodes": int, "edges": int, "falkor": "up"|"down"}
Returns HTTP 200 when FalkorDB is up, HTTP 503 when down.
Provides /health at the root per CONTRACT section 9 in addition to /api/health.
"""

from __future__ import annotations

import os
from fastapi import APIRouter, Response, status

health_router = APIRouter()

DEFAULT_TENANT = "northwind"
DEFAULT_GRAPH = f"faultline:{DEFAULT_TENANT}"


def check_falkordb() -> dict:
    falkor_url = os.environ.get("FALKOR_URL", "redis://localhost:6379")
    try:
        from graph.connection import client, get_graph
        c = client()
        c.connection.ping()
        g = get_graph()
        node_count = 0
        edge_count = 0
        try:
            res_nodes = g.ro_query("MATCH (n) RETURN count(n)").result_set
            res_edges = g.ro_query("MATCH ()-[r]->() RETURN count(r)").result_set
            node_count = int(res_nodes[0][0]) if res_nodes else 0
            edge_count = int(res_edges[0][0]) if res_edges else 0
        except Exception as q_err:
            if "empty key" not in str(q_err).lower():
                raise q_err
        return {
            "ok": True,
            "graph": g.name,
            "nodes": node_count,
            "edges": edge_count,
            "falkor": "up",
        }
    except Exception:
        return {
            "ok": False,
            "graph": DEFAULT_GRAPH,
            "nodes": 0,
            "edges": 0,
            "falkor": "down",
        }


@health_router.get("/health")
@health_router.get("/api/health")
def health(response: Response):
    info = check_falkordb()
    if info["falkor"] == "down":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return info
