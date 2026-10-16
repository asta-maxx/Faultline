"""Data models for Northwind Logistics structural entities and corpus items."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class PersonData:
    id: str
    name: str
    role: str
    team: str
    active: bool


@dataclass(frozen=True)
class SystemData:
    id: str
    name: str
    slug: str
    tier: int  # 1, 2, or 3
    owner_id: str


@dataclass(frozen=True)
class DecisionData:
    id: str
    ref: str  # e.g. "ADR-88"
    title: str
    status: Literal["accepted", "superseded", "rejected"]
    decided_at: int
    author_id: str
    supersedes_id: str | None = None  # Newer -> older
    text: str = ""


@dataclass
class DocumentData:
    id: str
    title: str
    path: str
    kind: Literal["runbook", "wiki", "spec", "readme"]
    updated_at: int
    author_id: str
    governs_system_ids: list[str] = field(default_factory=list)
    cites_decision_ids: list[str] = field(default_factory=list)
    text: str = ""
    factual_sentences: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TicketData:
    id: str
    ref: str
    title: str
    text: str
    state: str
    closed_at: int | None
    system_id: str | None = None


@dataclass(frozen=True)
class MessageData:
    id: str
    channel: str
    text: str
    sent_at: int
    author_id: str | None = None


@dataclass(frozen=True)
class PlantedConflictData:
    id: str
    kind: Literal["direct", "superseded", "undocumented"]
    entity_slug: str
    predicate: str
    source_a_id: str
    source_b_id: str
    evidence_span_a: str
    evidence_span_b: str
    correct_side: Literal["a", "b"]
    rationale: str
    expected_blast_radius: float
    side_a_blast_radius: float
    side_b_blast_radius: float
    governed_systems: list[str]
    doc_count: int
    citing_decisions: int


@dataclass(frozen=True)
class SubjectEntity:
    slug: str
    name: str
    type: Literal["system", "policy", "metric", "process", "artifact"]
    aliases: list[str]


@dataclass(frozen=True)
class FactRecord:
    sentence: str
    slug: str
    predicate: str
    canonical_value: str
    entity_type: Literal["system", "policy", "metric", "process", "artifact"]


@dataclass(frozen=True)
class PredicateSpec:
    name: str
    templates: list[str]
    canonical_values: list[Any]
    unit: str
