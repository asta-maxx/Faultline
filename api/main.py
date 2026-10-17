"""Faultline HTTP API (CONTRACT §9) under /api, and the MCP tools (§8) at /mcp.

    uv run --env-file .env uvicorn api.main:app --reload --port 8000

Live by default: every response is read from faultline:northwind (api/service.py).
FAULTLINE_FIXTURES=1 serves /fixtures/*.json instead, for frontend work without a graph.
The frontend Vite dev server proxies /api/* to this process.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.mcp_tools import mcp
from api import service, workspaces
from infra.app_patch.health import health_router
from infra.app_patch.static_mount import mount_spa

ROOT = Path(__file__).parent.parent
FIXTURES = ROOT / "fixtures"
FIXTURE_MODE = os.environ.get("FAULTLINE_FIXTURES") == "1"

# MCP tools (CONTRACT §8) share this process, mounted at /mcp (streamable HTTP).
mcp_app = mcp.http_app(path="/")
app = FastAPI(title="Faultline API", version="0.2.0", lifespan=mcp_app.lifespan)

# The Vite dev server's origin. In production FastAPI serves the built frontend itself.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health (CONTRACT §9), Dev C's router: /health and /api/health, 503 when FalkorDB is down.
app.include_router(health_router)

api = APIRouter(prefix="/api")


class ResolveBody(BaseModel):
    winner_claim_id: str
    rationale: str
    resolved_by: str


class DismissBody(BaseModel):
    rationale: str
    dismissed_by: str


class WorkspaceBody(BaseModel):
    name: str


class SourceBody(BaseModel):
    kind: str
    location: str
    token: str | None = None


def _errors(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except service.NotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except service.Invalid as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except (workspaces.Conflict, service.Conflicting) as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


def _tenant(workspace: str | None) -> str:
    """?workspace=<id> on the §9 endpoints (CONTRACT §9b); the default tenant when absent."""
    if workspace in (None, ""):
        return "northwind"
    return _errors(workspaces.require, workspace)["id"]


if FIXTURE_MODE:

    def _fixture(name: str) -> dict:
        path = FIXTURES / name
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"fixture {name} not found")
        return json.loads(path.read_text(encoding="utf-8"))

    @api.get("/stats")
    def fixture_stats():
        return _fixture("stats.json")

    @api.get("/conflicts")
    def fixture_conflicts(status: str | None = None, limit: int = Query(default=50, le=200)):
        data = _fixture("conflicts.json")
        rows = [c for c in data["conflicts"] if status in (None, "", "all") or c["status"] == status]
        rows = sorted(rows, key=lambda c: c["blast_radius"], reverse=True)[:limit]
        return {"conflicts": rows, "total": len(rows), "stats": data["stats"]}

    @api.get("/conflicts/{conflict_id}")
    def fixture_conflict(conflict_id: str):
        # Only conflict-01 has a full fixture; anything else is a 404, never a synthesised path.
        return _fixture(f"{conflict_id}.json")

else:

    @api.get("/stats")
    def get_stats(workspace: str | None = None):
        return service.stats(_tenant(workspace))

    @api.get("/conflicts")
    def list_conflicts(status: str | None = None, limit: int = Query(default=50, ge=1, le=200),
                       workspace: str | None = None):
        return service.list_conflicts(status, limit, tenant=_tenant(workspace))

    @api.get("/conflicts/{conflict_id}")
    def get_conflict(conflict_id: str, workspace: str | None = None):
        return _errors(service.get_conflict, conflict_id, tenant=_tenant(workspace))

    @api.post("/conflicts/{conflict_id}/resolve")
    def resolve_conflict(conflict_id: str, body: ResolveBody, workspace: str | None = None):
        return _errors(service.resolve, conflict_id, body.winner_claim_id, body.rationale, body.resolved_by,
                       tenant=_tenant(workspace))

    @api.post("/conflicts/{conflict_id}/dismiss")
    def dismiss_conflict(conflict_id: str, body: DismissBody, workspace: str | None = None):
        return _errors(service.dismiss, conflict_id, body.rationale, body.dismissed_by, tenant=_tenant(workspace))

    @api.post("/conflicts/{conflict_id}/draft")
    def draft_correction(conflict_id: str, workspace: str | None = None):
        return _errors(service.draft, conflict_id, tenant=_tenant(workspace))

    # Workspaces, sources and audits (CONTRACT §9b)
    @api.get("/workspaces")
    def list_workspaces():
        return workspaces.list_workspaces()

    @api.post("/workspaces")
    def create_workspace(body: WorkspaceBody):
        return _errors(workspaces.create_workspace, body.name)

    @api.get("/workspaces/{workspace_id}/sources")
    def list_sources(workspace_id: str):
        return _errors(workspaces.list_sources, workspace_id)

    @api.post("/workspaces/{workspace_id}/sources")
    def add_source(workspace_id: str, body: SourceBody):
        return _errors(workspaces.add_source, workspace_id, body.kind, body.location, body.token)

    @api.delete("/workspaces/{workspace_id}/sources/{source_id}")
    def delete_source(workspace_id: str, source_id: str):
        return _errors(workspaces.delete_source, workspace_id, source_id)

    @api.post("/workspaces/{workspace_id}/audit")
    def start_audit(workspace_id: str):
        return _errors(workspaces.start_audit, workspace_id)

    @api.get("/audits/{run_id}")
    def get_audit(run_id: str):
        return _errors(workspaces.get_audit, run_id)

    @api.post("/reingest")
    def reingest(x_reingest_token: str | None = Header(default=None)):
        expected = os.environ.get("REINGEST_TOKEN")
        if not expected:
            raise HTTPException(status_code=503, detail="reingest is disabled: REINGEST_TOKEN is not set")
        if x_reingest_token != expected:
            raise HTTPException(status_code=403, detail="X-Reingest-Token is missing or wrong")
        return {"job_id": service.start_reingest()}


app.include_router(api)
app.mount("/mcp", mcp_app)

# Built frontend with SPA fallback. Registered last so it never shadows an API route.
mount_spa(app, ROOT / "web" / "dist")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
