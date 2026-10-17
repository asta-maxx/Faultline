"""Integration test for data/seed.py against FalkorDB.
Automatically skipped if FalkorDB is unreachable.
"""

from __future__ import annotations

import pytest

from data.seed import seed_structural_graph
from graph.connection import DEFAULT_TENANT, client, get_graph


def is_falkordb_available() -> bool:
    try:
        c = client()
        c.connection.ping()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not is_falkordb_available(), reason="FalkorDB instance is unreachable")
def test_seed_structural_graph_integration():
    tenant = "test_northwind_seed"
    res = seed_structural_graph(tenant_id=tenant, reset=True, generator_seed=42)

    assert res["elapsed_seconds"] < 30.0

    # Node counts
    assert res["node_counts"]["Person"] == 60
    assert res["node_counts"]["System"] == 14
    assert res["node_counts"]["Decision"] == 40
    assert res["node_counts"]["Document"] == 312
    assert res["node_counts"]["Ticket"] == 400
    assert res["node_counts"]["Message"] == 2000

    # Edge counts
    assert res["edge_counts"]["OWNS"] == 14
    assert res["edge_counts"]["AUTHORED"] == 352
    assert res["edge_counts"]["SUPERSEDES"] == 26
    assert res["edge_counts"]["GOVERNS"] == 323
    assert res["edge_counts"]["CITES"] == 108

    # Verify no prohibited entities exist
    g = get_graph(tenant)
    for lbl in ("Claim", "Entity", "Conflict"):
        cnt = g.ro_query(f"MATCH (n:{lbl}) RETURN count(n)").result_set[0][0]
        assert cnt == 0, f"Found unexpected label {lbl}"

    for rel in ("ASSERTS", "ABOUT", "CONTRADICTS", "INVOLVES", "RESOLVED_AS"):
        cnt = g.ro_query(f"MATCH ()-[r:{rel}]->() RETURN count(r)").result_set[0][0]
        assert cnt == 0, f"Found unexpected relationship {rel}"

    # Cleanup test graph
    try:
        g.delete()
    except Exception:
        pass


@pytest.mark.skipif(not is_falkordb_available(), reason="FalkorDB instance is unreachable")
def test_seed_structural_graph_merge_integration():
    tenant = "test_northwind_merge"
    g = get_graph(tenant)
    try:
        g.delete()
    except Exception:
        pass

    # Pre-populate dummy document and claim (simulating surveyor)
    g.query("CREATE (:Document {id: 'doc-0001', title: 'Existing Doc', path: '/test', kind: 'handbook', updated_at: 1000})")
    g.query("CREATE (:Claim {id: 'test-claim-1', text: 'Some claim', confidence: 1.0})")
    g.query("MATCH (d:Document {id: 'doc-0001'}), (c:Claim {id: 'test-claim-1'}) CREATE (d)-[:ASSERTS]->(c)")

    # Run seed in merge mode
    res = seed_structural_graph(tenant_id=tenant, merge=True, generator_seed=42)

    assert res["node_counts"]["Person"] == 60
    assert res["node_counts"]["System"] == 14
    assert res["node_counts"]["Decision"] == 40
    assert res["node_counts"]["Document"] == 312
    assert res["node_counts"]["Ticket"] == 400
    assert res["node_counts"]["Message"] == 2000

    assert res["edge_counts"]["OWNS"] == 14
    assert res["edge_counts"]["AUTHORED"] == 352
    assert res["edge_counts"]["SUPERSEDES"] == 26
    assert res["edge_counts"]["GOVERNS"] == 323
    assert res["edge_counts"]["CITES"] == 108

    # Verify claim and ASSERTS edge were preserved
    claims_cnt = g.ro_query("MATCH (c:Claim) RETURN count(c)").result_set[0][0]
    assert claims_cnt == 1

    asserts_cnt = g.ro_query("MATCH ()-[r:ASSERTS]->() RETURN count(r)").result_set[0][0]
    assert asserts_cnt == 1

    # Verify no duplicate doc-0001
    doc_1_cnt = g.ro_query("MATCH (d:Document {id: 'doc-0001'}) RETURN count(d)").result_set[0][0]
    assert doc_1_cnt == 1

    # Cleanup test graph
    try:
        g.delete()
    except Exception:
        pass

