"""
Faultline API server — dev/demo entry point.

For the hackathon demo, this serves the fixture JSON files when FalkorDB is
not yet fully wired. When the real graph data is live, the responses here
will come from graph.queries rather than fixtures/.

Run with:
    uv run python -m api.main
    # or:
    uv run uvicorn api.main:app --reload --port 8000

The frontend Vite dev server proxies /api/* → http://localhost:8000.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).parent.parent
FIXTURES = ROOT / "fixtures"

app = FastAPI(title="Faultline API", version="0.1.0")

# Allow the Vite dev server origin during development.
# In production, FastAPI serves the built frontend directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_fixture(name: str) -> dict:
    path = FIXTURES / name
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"Fixture {name} not found")
    return json.loads(path.read_text(encoding="utf-8"))


# ── Health (CONTRACT §9) ──────────────────────────────────────────────────────
from infra.app_patch.health import health_router
app.include_router(health_router)


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats():
    return load_fixture("stats.json")


# ── Conflicts ─────────────────────────────────────────────────────────────────

@app.get("/api/conflicts")
def list_conflicts(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
):
    data = load_fixture("conflicts.json")
    conflicts = data["conflicts"]

    if status and status != "all":
        conflicts = [c for c in conflicts if c.get("status") == status]

    # Sort by blast_radius descending (default)
    conflicts = sorted(conflicts, key=lambda c: c["blast_radius"], reverse=True)
    conflicts = conflicts[:limit]

    return {
        "conflicts": conflicts,
        "total": len(data["conflicts"]),
        "stats": data.get("stats", {}),
    }


@app.get("/api/conflicts/{conflict_id}")
def get_conflict(conflict_id: str):
    # The fixture only covers conflict-01; for others, serve the summary from
    # the list fixture without a path (frontend handles missing path gracefully).
    detail_fixture = FIXTURES / f"{conflict_id}.json"
    if detail_fixture.exists():
        return json.loads(detail_fixture.read_text(encoding="utf-8"))

    # Fall back: find in conflicts.json and synthesise a minimal response.
    data = load_fixture("conflicts.json")
    match = next((c for c in data["conflicts"] if c["id"] == conflict_id), None)
    if not match:
        raise HTTPException(status_code=404, detail=f"Conflict {conflict_id!r} not found")

    # Minimal graph path from claims
    nodes = []
    edges = []
    for claim in match.get("claims", []):
        nodes.append({"id": claim["id"], "label": claim["text"][:60], "type": "claim", "state": claim.get("state")})
        src = claim.get("source", {})
        if src.get("doc_id"):
            if not any(n["id"] == src["doc_id"] for n in nodes):
                nodes.append({"id": src["doc_id"], "label": src.get("title", src["doc_id"]), "type": "document"})
            edges.append({"source": src["doc_id"], "target": claim["id"], "type": "ASSERTS"})

    # Add CONTRADICTS edge if both claims present
    claim_ids = [c["id"] for c in match.get("claims", [])]
    if len(claim_ids) >= 2:
        edges.append({"source": claim_ids[0], "target": claim_ids[1], "type": "CONTRADICTS"})

    return {
        "conflict": match,
        "path": {"nodes": nodes, "edges": edges},
    }


@app.post("/api/conflicts/{conflict_id}/resolve")
def resolve_conflict(conflict_id: str, body: dict):
    # In fixture mode, just acknowledge.
    return {"ok": True, "conflict": {"id": conflict_id, "status": "resolved"}}


# ── Serve built frontend (production) ────────────────────────────────────────
from infra.app_patch.static_mount import mount_spa
mount_spa(app, ROOT / "web" / "dist")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
