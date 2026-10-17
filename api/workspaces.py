"""Workspaces, sources and audits (CONTRACT §9b). Records in faultline:_registry; each
workspace's data in its own graph, faultline:{workspace_id}."""

from __future__ import annotations

import os
import time
from pathlib import Path

from agent import audit, gitsource
from api.service import Invalid, NotFound
from graph import registry
from graph.connection import get_graph
from graph.queries import rows
from graph.schema import apply_schema


class Conflict(Exception):
    pass


def _count(workspace_id: str, cypher: str) -> int:
    try:
        return rows(get_graph(workspace_id), cypher)[0]["n"]
    except Exception as e:  # a workspace whose graph holds nothing yet
        if "empty key" in str(e).lower():
            return 0
        raise


def _workspace(w: dict) -> dict:
    last = registry.latest_run(w["id"], status="done")
    newest = registry.latest_run(w["id"])
    return {
        "id": w["id"], "name": w["name"], "graph": w["graph"],
        "sources": len(registry.list_sources(w["id"])),
        "documents": _count(w["id"], "MATCH (d:Document) RETURN count(d) AS n"),
        "claims": _count(w["id"], "MATCH (c:Claim) RETURN count(c) AS n"),
        "conflicts": _count(w["id"], "MATCH (k:Conflict {status: 'open'}) RETURN count(k) AS n"),
        "last_audit": last["ended_at"] if last else None,
        "latest_run": ({"run_id": newest["run_id"], "status": newest["status"], "started_at": newest["started_at"]}
                       if newest else None),
    }


def require(workspace_id: str) -> dict:
    if not registry.valid_id(workspace_id):
        raise NotFound(f"workspace {workspace_id!r} not found")
    registry.bootstrap()
    w = registry.get_workspace(workspace_id)
    if not w:
        raise NotFound(f"workspace {workspace_id!r} not found")
    return w


def list_workspaces() -> list[dict]:
    registry.bootstrap()
    return [_workspace(w) for w in registry.list_workspaces()]


def create_workspace(name: str) -> dict:
    wid = registry.slugify(name or "")
    if not wid:
        raise Invalid("A workspace name needs at least one letter or digit.")
    registry.bootstrap()
    if registry.get_workspace(wid):
        raise Conflict(f"A workspace with id {wid!r} already exists. Choose another name.")
    w = registry.create_workspace(name)
    apply_schema(wid)  # creates faultline:{wid} with the §5 constraints and indexes
    return _workspace(w)


def list_sources(workspace_id: str) -> list[dict]:
    require(workspace_id)
    return registry.list_sources(workspace_id)


def _source_root() -> Path | None:
    root = os.environ.get("FAULTLINE_SOURCE_ROOT")
    return Path(root).resolve() if root else None


def add_source(workspace_id: str, kind: str, location: str, token: str | None) -> dict:
    require(workspace_id)
    location = (location or "").strip()
    if not location:
        raise Invalid("Enter a folder path or a repository URL.")
    if kind == "folder":
        if os.environ.get("FAULTLINE_ALLOW_FOLDERS", "1") == "0":
            raise Invalid("Folder sources are turned off on this server: it cannot see your computer's files. "
                          "Add a Git repository instead, or run Faultline yourself to audit a local folder.")
        folder = Path(location).expanduser().resolve()
        root = _source_root()
        if root and root != folder and root not in folder.parents:
            raise Invalid(f"Folder sources must be inside {root} on this server (FAULTLINE_SOURCE_ROOT).")
        if not folder.is_dir():
            raise Invalid(f"No folder at {folder} on the machine running the API.")
        n = len(audit.folder_files(folder))
        return registry.add_source(workspace_id, {
            "kind": "folder", "location": str(folder), "docs": n, "status": "ready", "has_token": False,
            "message": None if n else "No .md, .markdown or .txt files in this folder.",
        })
    if kind == "git":
        try:
            url = gitsource.validate_url(location)
            sid = registry.new_source_id()
            dest = gitsource.checkout_path(workspace_id, sid)
            gitsource.clone(url, dest, token or None)  # the token lives only for this call
        except gitsource.GitError as e:
            raise Invalid(str(e)) from e
        n = len(audit.folder_files(dest))
        return registry.add_source(workspace_id, {
            "kind": "git", "location": url, "docs": n, "status": "ready", "has_token": bool(token),
            "message": None if n else "Cloned, but it has no .md, .markdown or .txt files.",
        }, sid=sid)
    raise Invalid("kind must be 'folder' or 'git'.")


def delete_source(workspace_id: str, source_id: str) -> dict:
    require(workspace_id)
    if not registry.delete_source(workspace_id, source_id):
        raise NotFound(f"source {source_id!r} not found in workspace {workspace_id!r}")
    gitsource.remove(workspace_id, source_id)
    return {"ok": True}


def start_audit(workspace_id: str) -> dict:
    require(workspace_id)
    try:
        return {"run_id": audit.start(workspace_id)}
    except audit.AuditError as e:
        if "already running" in str(e):
            raise Conflict(str(e)) from e
        raise Invalid(str(e)) from e


def get_audit(run_id: str) -> dict:
    run = registry.get_run(run_id)
    if not run:
        raise NotFound(f"audit {run_id!r} not found")
    if run["status"] == "running" and run_id not in audit._running.values():
        # No thread in this process owns it: the server restarted while it ran.
        run.update(status="failed", error="The server restarted while this audit was running. Run it again.",
                   ended_at=run.get("ended_at") or int(time.time()), stage=None, current=None)
        for s in run["stages"]:
            if s["state"] == "active":
                s["state"] = "failed"
        registry.save_run(run)
    return run
