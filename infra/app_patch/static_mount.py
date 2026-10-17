"""SPA Static Files mounting patch for FastAPI in Faultline.

Mounts static assets and provides an SPA fallback handler for client-side routing.
Ensures API endpoints and OpenAPI docs are never shadowed.
"""

from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def mount_spa(app: FastAPI, web_dist: Path | str) -> None:
    """Mounts web/dist assets and registers the SPA fallback handler.

    Must be called AFTER all API routers have been registered on `app`.
    """
    dist_path = Path(web_dist)
    if not dist_path.exists():
        return

    assets_dir = dist_path / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # Paths that must NEVER return HTML
    EXACT_BLOCKED = {"health", "stats", "docs", "openapi.json"}

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        norm = full_path.strip("/")
        # Block only paths starting with "api/" plus exact paths "health", "stats", "docs", "openapi.json"
        # Note: "conflicts" prefixes are NOT blocked, so /conflicts and /conflicts/{id} route to SPA
        if norm.startswith("api/") or norm == "api" or norm in EXACT_BLOCKED:
            raise HTTPException(status_code=404, detail="Not Found")

        index_file = dist_path / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Frontend index.html not found")
