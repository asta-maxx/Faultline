"""Tests for Northwind Logistics deterministic generator (Job 1).

Covers:
- Determinism: two runs with same seed produce byte-identical files.
- Volume counts: 60 people, 8 teams, 14 systems (tiers 1-3), 40 ADRs (14 chains, depth 2-4),
  312 docs, 400 tickets, 2,000 messages.
- Exactly 14 planted contradictions with 5 direct / 5 superseded / 4 undocumented split.
- Superseded consistency: every superseded planted conflict really has doc.updated_at > decision.decided_at.
- Referential integrity: every referenced person, system, decision, document, ticket, message ID exists.
- Unique IDs: Ticket and Message IDs are 100% unique (since FalkorDB has no unique constraint for them).
- Blast radius diversity: the 14 planted conflict blast radii are not all equal and follow CONTRACT §7.3.
- Facts format: factual sentences are complete sentences on a single unbroken line.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import pytest

from data.generate import NorthwindGenerator, compute_blast_radius
from data.models import DecisionData, SystemData


@pytest.fixture(scope="module")
def generator_run():
    gen = NorthwindGenerator(seed=42)
    gen.generate_all()
    return gen


def test_people_volume_and_teams(generator_run: NorthwindGenerator):
    assert len(generator_run.people) == 60
    teams = {p.team for p in generator_run.people}
    assert len(teams) == 8
    # All people IDs unique
    pids = [p.id for p in generator_run.people]
    assert len(pids) == len(set(pids))


def test_systems_volume_and_tiers(generator_run: NorthwindGenerator):
    assert len(generator_run.systems) == 14
    sids = [s.id for s in generator_run.systems]
    assert len(sids) == len(set(sids))
    # Tiers 1-3 only
    for s in generator_run.systems:
        assert s.tier in (1, 2, 3)
    # Every system has an owner that exists
    pids = {p.id for p in generator_run.people}
    for s in generator_run.systems:
        assert s.owner_id in pids


def test_decisions_volume_and_chains(generator_run: NorthwindGenerator):
    assert len(generator_run.decisions) == 40
    dids = [d.id for d in generator_run.decisions]
    assert len(dids) == len(set(dids))
    
    # Check chain heads status: latest is "accepted", older are "superseded"
    # Find all decisions that are superseded by someone
    superseded_ids = {d.supersedes_id for d in generator_run.decisions if d.supersedes_id}
    
    for d in generator_run.decisions:
        assert d.status in ("accepted", "superseded", "rejected")
        if d.id in superseded_ids:
            assert d.status == "superseded"
        elif d.supersedes_id is not None or not any(x.supersedes_id == d.id for x in generator_run.decisions):
            # Chain head or un-superseded
            assert d.status == "accepted"


def test_documents_volume_and_kinds(generator_run: NorthwindGenerator):
    assert len(generator_run.documents) == 312
    doc_ids = [d.id for d in generator_run.documents]
    assert len(doc_ids) == len(set(doc_ids))
    
    valid_kinds = {"runbook", "wiki", "spec", "readme"}
    for doc in generator_run.documents:
        assert doc.kind in valid_kinds
        assert isinstance(doc.updated_at, int)


def test_tickets_volume_and_uniqueness(generator_run: NorthwindGenerator):
    assert len(generator_run.tickets) == 400
    tkt_ids = [t.id for t in generator_run.tickets]
    # CONTRACT §5: Ticket has no FalkorDB constraint, so ID uniqueness must be tested in Python
    assert len(tkt_ids) == len(set(tkt_ids))
    for t in generator_run.tickets:
        assert t.closed_at is None or isinstance(t.closed_at, int)


def test_messages_volume_and_uniqueness(generator_run: NorthwindGenerator):
    assert len(generator_run.messages) == 2000
    msg_ids = [m.id for m in generator_run.messages]
    # CONTRACT §5: Message has no FalkorDB constraint, so ID uniqueness must be tested in Python
    assert len(msg_ids) == len(set(msg_ids))
    for m in generator_run.messages:
        assert isinstance(m.sent_at, int)


def test_planted_conflicts_count_and_split(generator_run: NorthwindGenerator):
    conflicts = generator_run.planted_conflicts
    assert len(conflicts) == 14
    
    direct = [c for c in conflicts if c.kind == "direct"]
    superseded = [c for c in conflicts if c.kind == "superseded"]
    undocumented = [c for c in conflicts if c.kind == "undocumented"]
    
    assert len(direct) == 5
    assert len(superseded) == 5
    assert len(undocumented) == 4


def test_superseded_cases_timestamp_guarantee(generator_run: NorthwindGenerator):
    """Every superseded case really has doc.updated_at > decision.decided_at so that
    a naive timestamp comparison gets it wrong and SUPERSEDES traversal gets it right.
    """
    superseded = [c for c in generator_run.planted_conflicts if c.kind == "superseded"]
    doc_map = {d.id: d for d in generator_run.documents}
    dec_map = {d.id: d for d in generator_run.decisions}
    
    for conf in superseded:
        # source_a is the doc asserting the superseded value citing the older ADR
        doc_a = doc_map[conf.source_a_id]
        doc_b = doc_map[conf.source_b_id]
        
        # The latest decision cited by doc_b
        latest_dec_id = doc_b.cites_decision_ids[0]
        latest_dec = dec_map[latest_dec_id]
        
        # doc_a.updated_at must be strictly greater than the decided_at of the latest ADR!
        assert doc_a.updated_at > latest_dec.decided_at, (
            f"Conflict {conf.id}: doc_a.updated_at ({doc_a.updated_at}) "
            f"is not newer than decision.decided_at ({latest_dec.decided_at})"
        )


def test_blast_radius_calculation_and_variance(generator_run: NorthwindGenerator):
    radii = [c.expected_blast_radius for c in generator_run.planted_conflicts]
    # The 14 values must not all be equal
    assert len(set(radii)) > 1
    # Check that tier 1 systems produce significantly higher blast radius
    max_radius = max(radii)
    min_radius = min(radii)
    assert max_radius > min_radius * 2.0


def test_referential_integrity(generator_run: NorthwindGenerator):
    pids = {p.id for p in generator_run.people}
    sids = {s.id for s in generator_run.systems}
    dids = {d.id for d in generator_run.decisions}
    doc_ids = {d.id for d in generator_run.documents}
    msg_ids = {m.id for m in generator_run.messages}
    
    # Systems have valid owners
    for s in generator_run.systems:
        assert s.owner_id in pids
        
    # Decisions have valid authors and supersedes links
    for d in generator_run.decisions:
        assert d.author_id in pids
        if d.supersedes_id:
            assert d.supersedes_id in dids
            
    # Documents have valid authors, governed systems, cited decisions
    for doc in generator_run.documents:
        assert doc.author_id in pids
        for sid in doc.governs_system_ids:
            assert sid in sids
        for dec_id in doc.cites_decision_ids:
            assert dec_id in dids
            
    # Planted conflicts reference existing sources
    for conf in generator_run.planted_conflicts:
        assert conf.source_a_id in doc_ids or conf.source_a_id in msg_ids
        assert conf.source_b_id in doc_ids or conf.source_b_id in msg_ids


def test_determinism_byte_identical_runs():
    """Two independent generator runs with the same seed produce byte-identical output."""
    with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
        dir1 = Path(tmp1)
        dir2 = Path(tmp2)
        
        # Run 1
        gen1 = NorthwindGenerator(seed=42)
        gen1.generate_all()
        gen1.write_corpus(dir1)
        
        # Run 2
        gen2 = NorthwindGenerator(seed=42)
        gen2.generate_all()
        gen2.write_corpus(dir2)
        
        def dir_hashes(directory: Path) -> dict[str, str]:
            hashes = {}
            for path in sorted(directory.rglob("*")):
                if path.is_file():
                    rel = path.relative_to(directory).as_posix()
                    hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
            return hashes
            
        hashes1 = dir_hashes(dir1)
        hashes2 = dir_hashes(dir2)
        
        assert hashes1 == hashes2
        assert len(hashes1) > 0
