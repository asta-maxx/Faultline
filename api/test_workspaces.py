"""Workspaces, sources and audit guards (CONTRACT §9b). No LLM calls: audits are only started
where they must be refused. Skipped when FalkorDB is unreachable.

    uv run --env-file .env pytest api -q
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from graph import registry
from graph.connection import client, get_graph

NAME = "Pytest Workspace"
WID = "pytest-workspace"


def falkor_up() -> bool:
    try:
        client().connection.ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not falkor_up(), reason="FalkorDB instance is unreachable")


def _cleanup() -> None:
    registry._g().query("MATCH (w:Workspace {id: $id}) OPTIONAL MATCH (w)-[]->(x) DETACH DELETE w, x", {"id": WID})
    try:
        get_graph(WID).delete()
    except Exception:
        pass


@pytest.fixture(scope="module")
def api():
    _cleanup()
    with TestClient(app) as c:
        yield c
    _cleanup()


def test_create_list_and_isolation(api):
    r = api.post("/api/workspaces", json={"name": NAME})
    assert r.status_code == 200, r.text
    w = r.json()
    assert (w["id"], w["graph"], w["claims"], w["conflicts"], w["latest_run"]) == (WID, f"faultline:{WID}", 0, 0, None)
    assert api.post("/api/workspaces", json={"name": "pytest  workspace!"}).status_code == 409
    assert api.post("/api/workspaces", json={"name": "!!!"}).status_code == 422
    assert WID in {x["id"] for x in api.get("/api/workspaces").json()}

    # Each workspace is its own graph: the new one sees none of the default tenant's conflicts.
    stats = api.get(f"/api/stats?workspace={WID}").json()
    assert (stats["claims"], stats["conflicts_open"]) == (0, 0)
    assert api.get(f"/api/conflicts?workspace={WID}").json()["conflicts"] == []
    assert api.get("/api/stats?workspace=no-such-workspace").status_code == 404
    assert api.get("/api/stats?workspace=_registry").status_code == 404


def test_sources_are_honest(api, tmp_path, monkeypatch):
    (tmp_path / "a.md").write_text("# A\nThe window is 30 days.\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("The window is 45 days.\n", encoding="utf-8")
    (tmp_path / "skip.pdf").write_bytes(b"%PDF")

    folder = api.post(f"/api/workspaces/{WID}/sources", json={"kind": "folder", "location": str(tmp_path)}).json()
    assert (folder["status"], folder["docs"], folder["has_token"]) == ("ready", 2, False)

    git = api.post(f"/api/workspaces/{WID}/sources",
                   json={"kind": "git", "location": "https://example.com/r.git", "token": "tok-123"}).json()
    assert git["status"] == "unsupported" and git["has_token"] is True and "not implemented" in git["message"]
    stored = registry._g().query("MATCH (s:Source {id: $id}) RETURN s", {"id": git["id"]}).result_set[0][0]
    assert "tok-123" not in str(stored.properties)  # the token is never stored

    assert api.post(f"/api/workspaces/{WID}/sources",
                    json={"kind": "folder", "location": str(tmp_path / "missing")}).status_code == 422
    assert api.post(f"/api/workspaces/{WID}/sources", json={"kind": "ftp", "location": "x"}).status_code == 422

    monkeypatch.setenv("FAULTLINE_SOURCE_ROOT", str(tmp_path / "elsewhere"))
    assert api.post(f"/api/workspaces/{WID}/sources", json={"kind": "folder", "location": str(tmp_path)}).status_code == 422
    monkeypatch.delenv("FAULTLINE_SOURCE_ROOT")

    listed = api.get(f"/api/workspaces/{WID}/sources").json()
    assert {s["id"] for s in listed} == {folder["id"], git["id"]}

    # An audit needs a readable folder: with only the git source left, it is refused, not faked.
    assert api.delete(f"/api/workspaces/{WID}/sources/{folder['id']}").json() == {"ok": True}
    assert api.delete(f"/api/workspaces/{WID}/sources/{folder['id']}").status_code == 404
    r = api.post(f"/api/workspaces/{WID}/audit")
    assert r.status_code == 422 and "No readable source" in r.json()["detail"]
    assert api.get("/api/audits/run-does-not-exist").status_code == 404


def test_audit_left_running_by_a_restart_reads_as_failed(api):
    # A run the registry still calls "running" but no thread in this process owns.
    registry.save_run({"run_id": "run-orphan-test", "workspace_id": WID, "status": "running", "stage": "EXTRACTING CLAIMS",
                       "current": "a.md", "error": None, "summary": None, "started_at": 1, "ended_at": None,
                       "stages": [{"name": "EXTRACTING CLAIMS", "state": "active", "count": 3, "unit": "claims",
                                   "detail": None, "started_at": 1, "ended_at": None}]})
    run = api.get("/api/audits/run-orphan-test").json()
    assert run["status"] == "failed" and "restarted" in run["error"]
    assert run["stages"][0]["state"] == "failed"
    assert registry.get_run("run-orphan-test")["status"] == "failed"  # persisted, not only reported


def test_dismiss_route_and_mcp_workspace(api):
    assert api.post("/api/conflicts/nope/dismiss", json={"rationale": "r", "dismissed_by": "b"}).status_code == 404
    import asyncio

    from fastmcp import Client

    from agent.mcp_tools import mcp

    async def call():
        async with Client(mcp) as c:
            own = (await c.call_tool("find_candidates", {"workspace": WID})).data
            bad = (await c.call_tool("blast_radius", {"claim_id": "x", "workspace": "_registry"})).data
            return own, bad

    own, bad = asyncio.run(call())
    assert own["naive_pair_count"] == 0  # the empty pytest workspace, not northwind
    assert "not a valid workspace id" in bad["error"]
