"""Tests for infra/app_patch/static_mount.py"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app(tmp_path):
    """Create a minimal FastAPI app with mount_spa applied over a fake dist/."""
    from infra.app_patch.static_mount import mount_spa

    # Build a fake dist/ with index.html and a root-level SVG
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>SPA</html>")
    (dist / "faultline.svg").write_bytes(b"<svg/>")
    (dist / "favicon.ico").write_bytes(b"\x00" * 4)

    # Also create assets/ sub-dir (mounted separately)
    assets = dist / "assets"
    assets.mkdir()
    (assets / "main.js").write_bytes(b"console.log(1)")

    app = FastAPI()

    # Register a real /api route so 404 comes from API not fallback
    @app.get("/api/things")
    def things():
        return {"ok": True}

    mount_spa(app, dist)
    return TestClient(app, raise_server_exceptions=False)


# ── Root static file is served as a file (not index.html) ────────────────────

def test_root_svg_served(tmp_path):
    client = _make_app(tmp_path)
    r = client.get("/faultline.svg")
    assert r.status_code == 200
    assert b"<svg" in r.content


def test_root_favicon_served(tmp_path):
    client = _make_app(tmp_path)
    r = client.get("/favicon.ico")
    assert r.status_code == 200


# ── Path traversal is rejected ────────────────────────────────────────────────

def test_dotdot_returns_spa_not_sensitive_file(tmp_path):
    """/../etc/passwd gets normalised by Starlette to a SPA route.

    The key assertion is that the response body is our SPA HTML,
    NOT the content of any file outside dist/.
    """
    # Create a sensitive file next to dist/ to verify it's never served
    (tmp_path / "secret.txt").write_text("TOP SECRET")
    client = _make_app(tmp_path)
    r = client.get("/../secret.txt")
    # Starlette normalises ../ so the handler sees "secret.txt" as an unknown
    # path segment — it must NOT serve the parent-dir file because resolve()
    # stays inside dist/ (the file doesn't exist there).
    assert b"TOP SECRET" not in r.content
    assert b"SPA" in r.content  # Falls back to index.html


def test_dotdot_encoded_returns_spa_not_file(tmp_path):
    """Percent-encoded traversal must not serve files outside dist/."""
    (tmp_path / "secret.txt").write_text("TOP SECRET")
    client = _make_app(tmp_path)
    r = client.get("/%2e%2e/secret.txt")
    assert b"TOP SECRET" not in r.content


# ── SPA routes return index.html ──────────────────────────────────────────────

def test_spa_conflict_route(tmp_path):
    client = _make_app(tmp_path)
    r = client.get("/conflicts/abc-123")
    assert r.status_code == 200
    assert b"SPA" in r.content


def test_spa_root(tmp_path):
    client = _make_app(tmp_path)
    r = client.get("/")
    assert r.status_code == 200
    assert b"SPA" in r.content


def test_spa_settings(tmp_path):
    client = _make_app(tmp_path)
    r = client.get("/settings")
    assert r.status_code == 200
    assert b"SPA" in r.content


# ── API / reserved paths return JSON 404, not HTML ───────────────────────────

def test_api_nonexistent_returns_json_404(tmp_path):
    client = _make_app(tmp_path)
    r = client.get("/api/nonexistent")
    assert r.status_code == 404
    data = r.json()
    assert "detail" in data  # JSON, not HTML


def test_health_not_html(tmp_path):
    client = _make_app(tmp_path)
    r = client.get("/health")
    # 404 JSON (health router not wired here) — must not be SPA HTML
    assert r.status_code == 404
    assert b"SPA" not in r.content


def test_docs_not_html(tmp_path):
    client = _make_app(tmp_path)
    r = client.get("/docs")
    # FastAPI serves /docs itself if not blocked; if blocked → 404
    # Either way it must NOT return the SPA index content
    assert b"SPA" not in r.content


def test_mcp_not_html(tmp_path):
    client = _make_app(tmp_path)
    r = client.get("/mcp")
    assert r.status_code == 404
    assert b"SPA" not in r.content


def test_mcp_subpath_not_html(tmp_path):
    client = _make_app(tmp_path)
    r = client.get("/mcp/something")
    assert r.status_code == 404
    assert b"SPA" not in r.content
