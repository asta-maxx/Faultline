"""SPA Static Files mounting patch for FastAPI in Faultline.

Mounts static assets and provides an SPA fallback handler for client-side routing.
Ensures API endpoints and OpenAPI docs are never shadowed.

Root-level files (e.g. /faultline.svg, /favicon.ico) are served directly as
FileResponse if they exist in dist/; otherwise the SPA index.html is returned.
Path traversal (../, encoded variants, symlinks leaving dist) is rejected with 404.
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

    dist_resolved = dist_path.resolve()

    assets_dir = dist_path / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # Paths that must NEVER return HTML
    EXACT_BLOCKED = {"health", "stats", "docs", "openapi.json"}
    PREFIX_BLOCKED = ("api/", "mcp", "mcp/")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        norm = full_path.strip("/")

        # Block API, health, docs, mcp — these must never fall through to HTML
        if norm == "api" or norm in EXACT_BLOCKED:
            raise HTTPException(status_code=404, detail="Not Found")
        for prefix in PREFIX_BLOCKED:
            if norm == prefix.rstrip("/") or norm.startswith(prefix):
                raise HTTPException(status_code=404, detail="Not Found")

        # Serve root-level static files (e.g. /faultline.svg, /favicon.ico)
        # only if the path segment has no sub-directory (i.e. it's a root file)
        # and the resolved path stays strictly inside dist/.
        if norm and "/" not in norm:
            candidate = dist_path / norm
            try:
                resolved = candidate.resolve()
            except OSError:
                resolved = None
            if (
                resolved is not None
                and resolved.is_file()
                and not resolved.is_symlink()
                and resolved.is_relative_to(dist_resolved)
            ):
                return FileResponse(str(resolved))

        # SPA fallback: all other paths (e.g. /conflicts/abc, /settings) → index.html
        index_file = dist_path / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Frontend index.html not found")
