"""Workspace registry (CONTRACT §9b): one more graph in the same FalkorDB, faultline:_registry.

Workspaces, their sources and their audit runs are nodes here. Each workspace's data lives in
its own graph, faultline:{workspace_id}; nothing in this module ever writes to one of those.
Raw Cypher, plain dicts, like graph/queries.py.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from typing import Any

from graph.connection import DEFAULT_TENANT, client, get_graph, graph_name
from graph.queries import rows

REGISTRY = "_registry"  # faultline:_registry; a slug can never contain "_", so no workspace collides
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _g():
    return get_graph(REGISTRY)


def _graph_exists(workspace_id: str) -> bool:
    names = client().connection.execute_command("GRAPH.LIST")
    names = {n.decode() if isinstance(n, bytes) else n for n in names}
    return graph_name(workspace_id) in names


def bootstrap() -> None:
    """Register the default tenant when its graph exists but no Workspace node does yet."""
    if _graph_exists(DEFAULT_TENANT) and not get_workspace(DEFAULT_TENANT):
        _g().query("MERGE (w:Workspace {id: $id}) ON CREATE SET w.name = $name, w.graph = $graph, w.created_at = $at",
                   {"id": DEFAULT_TENANT, "name": DEFAULT_TENANT.capitalize(), "graph": graph_name(DEFAULT_TENANT),
                    "at": int(time.time())})


def _safe_rows(cypher: str, params: dict[str, Any] | None = None) -> list[dict]:
    try:
        return rows(_g(), cypher, params)
    except Exception as e:  # an empty registry graph does not exist yet; reads then return nothing
        if "empty key" in str(e).lower():
            return []
        raise


# ------------------------------------------------------------------ workspaces
def get_workspace(workspace_id: str) -> dict | None:
    found = _safe_rows("MATCH (w:Workspace {id: $id}) RETURN w.id AS id, w.name AS name, w.graph AS graph",
                       {"id": workspace_id})
    return found[0] if found else None


def list_workspaces() -> list[dict]:
    return _safe_rows("MATCH (w:Workspace) RETURN w.id AS id, w.name AS name, w.graph AS graph ORDER BY w.created_at, w.id")


def create_workspace(name: str) -> dict:
    wid = slugify(name)
    _g().query("CREATE (w:Workspace {id: $id, name: $name, graph: $graph, created_at: $at})",
               {"id": wid, "name": name.strip(), "graph": graph_name(wid), "at": int(time.time())})
    return {"id": wid, "name": name.strip(), "graph": graph_name(wid)}


# ------------------------------------------------------------------ sources
SOURCE_FIELDS = ("id", "kind", "location", "docs", "claims", "status", "message", "has_token", "added_at", "last_read_at")
_SOURCE_RETURN = ", ".join(f"s.{f} AS {f}" for f in SOURCE_FIELDS)


def list_sources(workspace_id: str) -> list[dict]:
    return _safe_rows(f"MATCH (:Workspace {{id: $ws}})-[:HAS_SOURCE]->(s:Source) RETURN {_SOURCE_RETURN} "
                      f"ORDER BY s.added_at, s.id", {"ws": workspace_id})


def new_source_id() -> str:
    return "src-" + uuid.uuid4().hex[:10]


def add_source(workspace_id: str, source: dict, sid: str | None = None) -> dict:
    sid = sid or new_source_id()
    record = {"id": sid, "added_at": int(time.time()), "last_read_at": None, "claims": None, **source}
    _g().query("MATCH (w:Workspace {id: $ws}) CREATE (w)-[:HAS_SOURCE]->(s:Source) SET s = $props",
               {"ws": workspace_id, "props": {k: v for k, v in record.items() if v is not None}})
    return {f: record.get(f) for f in SOURCE_FIELDS}


def update_source(source_id: str, **props: Any) -> None:
    _g().query("MATCH (s:Source {id: $id}) SET s += $props", {"id": source_id, "props": props})


def delete_source(workspace_id: str, source_id: str) -> bool:
    res = _g().query("MATCH (:Workspace {id: $ws})-[:HAS_SOURCE]->(s:Source {id: $id}) DETACH DELETE s RETURN 1",
                     {"ws": workspace_id, "id": source_id})
    return bool(res.result_set)


# ------------------------------------------------------------------ audit runs
def save_run(run: dict) -> None:
    """Upsert an audit run. Stages and summary are JSON strings: FalkorDB properties are scalars."""
    props = {k: v for k, v in run.items() if k not in ("stages", "summary") and v is not None}
    props["stages_json"] = json.dumps(run["stages"])
    props["summary_json"] = json.dumps(run["summary"])
    _g().query("MATCH (w:Workspace {id: $ws}) MERGE (w)-[:RAN]->(r:AuditRun {run_id: $id}) SET r += $props",
               {"ws": run["workspace_id"], "id": run["run_id"], "props": props})


def _run(row: dict) -> dict:
    r = dict(row["r"])
    r.pop("labels", None)
    r["stages"] = json.loads(r.pop("stages_json", "[]"))
    r["summary"] = json.loads(r.pop("summary_json", "null"))
    for k in ("stage", "current", "error", "ended_at"):
        r.setdefault(k, None)
    return r


def get_run(run_id: str) -> dict | None:
    found = _safe_rows("MATCH (r:AuditRun {run_id: $id}) RETURN r", {"id": run_id})
    return _run(found[0]) if found else None


def latest_run(workspace_id: str, status: str | None = None) -> dict | None:
    found = _safe_rows("MATCH (r:AuditRun {workspace_id: $ws}) WHERE $status IS NULL OR r.status = $status "
                       "RETURN r ORDER BY r.started_at DESC LIMIT 1", {"ws": workspace_id, "status": status})
    return _run(found[0]) if found else None


def valid_id(workspace_id: str) -> bool:
    return bool(SLUG.match(workspace_id or ""))
