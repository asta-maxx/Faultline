"""Adjudicator and live API against a throwaway graph, with a fake judge (no quota spent).

Skipped when FalkorDB is unreachable. Run with:  uv run --env-file .env pytest agent -q
"""

from __future__ import annotations

import json

import pytest

from agent import adjudicator, llm
from api import service
from graph.connection import client, get_graph
from graph.schema import apply_schema

TENANT = "test-adjudicator"
CONTRACT_EDGES = {"ASSERTS", "ABOUT", "CONTRADICTS", "SUPERSEDES", "CITES", "GOVERNS", "AUTHORED", "OWNS",
                  "DERIVED_FROM", "INVOLVES", "RESOLVED_AS"}
FIXTURE = json.loads(open("fixtures/conflict-01.json", encoding="utf-8").read())


def falkor_up() -> bool:
    try:
        client().connection.ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not falkor_up(), reason="FalkorDB instance is unreachable")

SEED = """
CREATE (old:Decision {id: 'dec-old', ref: 'ADR-1', title: 'Old', status: 'superseded', decided_at: 100}),
       (new:Decision {id: 'dec-new', ref: 'ADR-2', title: 'New', status: 'accepted', decided_at: 200}),
       (new)-[:SUPERSEDES]->(old),
       (sys:System {id: 'sys-a', name: 'System A', tier: 1}),
       (p:Person {id: 'p-1', name: 'R. Menon', role: 'Lead', active: true}),
       (p)-[:OWNS]->(sys),
       (d1:Document {id: 'doc-1', title: 'Runbook', path: 'runbooks/a.md', kind: 'runbook', updated_at: 300}),
       (d2:Document {id: 'doc-2', title: 'Policy', path: 'specs/a.md', kind: 'spec', updated_at: 250}),
       (d3:Document {id: 'doc-3', title: 'FAQ', path: 'wiki/b.md', kind: 'wiki', updated_at: 260}),
       (d4:Document {id: 'doc-4', title: 'Guide', path: 'wiki/c.md', kind: 'wiki', updated_at: 270}),
       (m:Message {id: 'msg-1', channel: '#ops', text: 'we cut it to 4s', sent_at: 400}),
       (d1)-[:CITES]->(old), (d2)-[:CITES]->(new), (d1)-[:GOVERNS]->(sys), (d2)-[:GOVERNS]->(sys),
       (e1:Entity {id: 'limit', name: 'Limit', type: 'policy'}),
       (e2:Entity {id: 'window', name: 'Window', type: 'policy'}),
       (e3:Entity {id: 'timeout', name: 'Timeout', type: 'system'})
"""

CLAIMS = [
    # superseded: runbook cites the old decision, policy cites the one that supersedes it
    ("c-1", "doc-1", "limit", "tolerance", "30 minutes", "Loads above 8 C for 30 minutes are rejected."),
    ("c-2", "doc-2", "limit", "tolerance", "15 minutes", "Loads above 8 C for 15 minutes are rejected."),
    # direct: no decisions on either side
    ("c-3", "doc-3", "window", "dispute_window", "30 days", "Invoices can be disputed within 30 days."),
    ("c-4", "doc-4", "window", "dispute_window", "45 days", "Invoices can be disputed within 45 days."),
    # undocumented: one side only in a message
    ("c-5", "doc-3", "timeout", "timeout", "10 seconds", "Router requests time out after 10 seconds."),
    ("c-6", "msg-1", "timeout", "timeout", "4 seconds", "Router requests time out after 4 seconds."),
]


@pytest.fixture(scope="module")
def graph():
    g = get_graph(TENANT)
    try:
        g.delete()
    except Exception:
        pass
    g = get_graph(TENANT)
    apply_schema(TENANT)
    g.query(SEED)
    for cid, src, ent, pred, obj, text in CLAIMS:
        g.query("MATCH (s {id: $src}), (e:Entity {id: $ent}) "
                "CREATE (s)-[:ASSERTS]->(:Claim {id: $id, text: $text, polarity: 'affirm', subject_ref: $ent, "
                "predicate: $pred, object: $obj, evidence_span: $text, confidence: 0.9, extracted_at: 1})-[:ABOUT]->(e)",
                {"src": src, "ent": ent, "id": cid, "text": text, "pred": pred, "obj": obj})
    yield g
    g.delete()


@pytest.fixture()
def fake_judge(monkeypatch):
    calls = []

    def generate(role, prompt, content, **params):
        calls.append(content)
        out = {"verdict": "contradicts", "confidence": 0.9, "evidence_span": "not in either claim", "reasoning": "x"}
        return llm.Result(json.dumps(out), "test:fake-judge", cached=False)

    monkeypatch.setattr(adjudicator.llm, "generate", generate)
    return calls


def test_adjudicate_writes_one_conflict_per_disagreement(graph, fake_judge):
    st = adjudicator.adjudicate(TENANT, workers=1)
    assert (st.prefiltered, st.groups, st.conflicts_written, st.failures) == (3, 3, 3, [])
    kinds = {r["kind"] for r in service.rows(graph, "MATCH (k:Conflict) RETURN k.kind AS kind")}
    assert kinds == {"superseded", "direct", "undocumented"}
    method = service.rows(graph, "MATCH ()-[r:CONTRADICTS]->() RETURN DISTINCT r.method AS m")
    assert method == [{"m": "fake-judge"}]
    # The judge's span was not literal text from either claim, so a claim's own span replaced it.
    spans = {r["s"] for r in service.rows(graph, "MATCH ()-[r:CONTRADICTS]->() RETURN r.evidence_span AS s")}
    assert all(any(s in c[5] for c in CLAIMS) for s in spans)

    # Judged pairs drop out of §7.1, so a second run judges nothing and writes nothing.
    again = adjudicator.adjudicate(TENANT, workers=1)
    assert (again.prefiltered, again.conflicts_written) == (0, 0)

    # Another document repeating one side's value is a new unjudged pair for the same
    # disagreement: it is skipped, and the Conflict keeps exactly two claims.
    graph.query("MATCH (d:Document {id: 'doc-4'}), (e:Entity {id: 'limit'}) "
                "CREATE (d)-[:ASSERTS]->(:Claim {id: 'c-7', text: 'Loads above 8 C for 30 minutes are rejected.', "
                "polarity: 'affirm', subject_ref: 'limit', predicate: 'tolerance', object: '30 minutes', "
                "evidence_span: 'for 30 minutes', confidence: 0.9, extracted_at: 1})-[:ABOUT]->(e)")
    calls_before = len(fake_judge)
    third = adjudicator.adjudicate(TENANT, workers=1)
    assert (third.prefiltered, third.already_surfaced, third.conflicts_written) == (1, 1, 0)
    assert len(fake_judge) == calls_before
    counts = service.rows(graph, "MATCH (k:Conflict)-[i:INVOLVES]->() RETURN k.id AS k, count(i) AS n")
    assert all(r["n"] == 2 for r in counts)


def test_api_shapes_match_the_fixture(graph, fake_judge):
    if not service.rows(graph, "MATCH (k:Conflict) RETURN count(k) AS n")[0]["n"]:
        adjudicator.adjudicate(TENANT, workers=1)
    listing = service.list_conflicts(None, 50, tenant=TENANT)
    assert listing["total"] == 3
    fixture_conflict_keys = set(FIXTURE["conflict"])
    for c in listing["conflicts"]:
        assert fixture_conflict_keys <= set(c)
        assert {cl["side"] for cl in c["claims"]} == {"a", "b"}
        assert set(c["claims"][0]["source"]) == set(FIXTURE["conflict"]["claims"][0]["source"])

    sup = next(c for c in listing["conflicts"] if c["kind"] == "superseded")
    states = {cl["source"]["doc_id"]: cl["state"] for cl in sup["claims"]}
    assert states == {"doc-1": "superseded", "doc-2": "live"}
    assert sup["owner"] == {"id": "p-1", "name": "R. Menon", "role": "Lead"}

    und = next(c for c in listing["conflicts"] if c["kind"] == "undocumented")
    assert {cl["source"]["doc_id"]: cl["state"] for cl in und["claims"]} == {"doc-3": "contradicted", "msg-1": "live"}

    detail = service.get_conflict(sup["id"], tenant=TENANT)
    path = detail["path"]
    assert 0 < len(path["nodes"]) <= service.PATH_CAP
    assert {e["type"] for e in path["edges"]} <= CONTRACT_EDGES
    ids = {n["id"] for n in path["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in path["edges"])
    assert {"SUPERSEDES", "CITES", "GOVERNS", "ASSERTS", "CONTRADICTS", "ABOUT", "OWNS"} <= {e["type"] for e in path["edges"]}
    dated = {n["id"]: n.get("at") for n in path["nodes"]}
    assert dated["dec-old"] == 100 and dated["doc-1"] == 300 and "at" not in next(n for n in path["nodes"] if n["type"] == "system")


def test_resolve_writes_resolved_as_and_rescores(graph, fake_judge):
    if not service.rows(graph, "MATCH (k:Conflict) RETURN count(k) AS n")[0]["n"]:
        adjudicator.adjudicate(TENANT, workers=1)
    direct = next(c for c in service.list_conflicts("open", 50, tenant=TENANT)["conflicts"] if c["kind"] == "direct")
    winner = direct["claims"][1]["id"]
    with pytest.raises(service.Invalid):
        service.resolve(direct["id"], "not-a-side", "r", "me", tenant=TENANT)
    out = service.resolve(direct["id"], winner, "Finance owns the window.", "R. Menon", tenant=TENANT)
    c = out["conflict"]
    assert c["status"] == "resolved"
    assert c["resolution"]["winner_claim_id"] == winner and c["resolution"]["resolved_by"] == "R. Menon"
    assert {cl["id"]: cl["state"] for cl in c["claims"]}[winner] == "live"
    assert service.stats(TENANT)["conflicts_resolved"] == 1
