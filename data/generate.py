"""Deterministic, seeded generator for Northwind Logistics corpus and structural graph.

Volumes:
  - 60 people across 8 teams
  - 312 documents (runbooks, wikis, specs, READMEs)
  - 40 ADRs with SUPERSEDES chains 2-4 deep
  - 400 tickets
  - 2,000 chat messages
  - 14 core systems across tiers 1-3
  - Exactly 14 planted contradictions: 5 direct, 5 superseded, 4 undocumented

Usage:
  python -m data.generate --seed 42 --out data/out
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from pathlib import Path

from data.adr_chains import generate_decisions
from data.constants import CHANNELS, PEOPLE_RAW, SUBJECT_ALIASES, SYSTEMS_RAW, TEAMS
from data.models import (
    DecisionData,
    DocumentData,
    MessageData,
    PersonData,
    PlantedConflictData,
    SystemData,
    TicketData,
)


def compute_blast_radius(systems: list[SystemData], doc_count: int, citing_decisions: int) -> float:
    """Computes blast radius per CONTRACT §7.3:
    tier_weight = sum(4 - s.tier for s in distinct governed systems)
    blast_radius = (tier_weight * 2.0) + doc_count + (citing_decisions * 1.5)
    """
    # Deduplicate systems by id
    distinct_systems = {s.id: s for s in systems if s.id}
    tier_weight = sum(4 - s.tier for s in distinct_systems.values())
    return float((tier_weight * 2.0) + doc_count + (citing_decisions * 1.5))


class NorthwindGenerator:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
        
        # Base epoch timestamps (deterministic, fixed reference 2025/2026)
        self.base_time = 1735689600  # 2025-01-01 00:00:00 UTC
        
        # Generated collections
        self.people: list[PersonData] = []
        self.systems: list[SystemData] = []
        self.decisions: list[DecisionData] = []
        self.documents: list[DocumentData] = []
        self.tickets: list[TicketData] = []
        self.messages: list[MessageData] = []
        self.planted_conflicts: list[PlantedConflictData] = []

    def build_people(self) -> None:
        """Generates exactly 60 people partitioned across 8 teams."""
        self.people.clear()
        for i, (name, role, team, active) in enumerate(PEOPLE_RAW, start=1):
            pid = f"usr-{i:04d}"
            self.people.append(PersonData(id=pid, name=name, role=role, team=team, active=active))

    def build_systems(self) -> None:
        """Generates the 14 core systems with tiers and owners."""
        self.systems.clear()
        for sid, name, slug, tier, owner_id in SYSTEMS_RAW:
            self.systems.append(SystemData(id=sid, name=name, slug=slug, tier=tier, owner_id=owner_id))

    def build_decisions(self) -> None:
        """Generates the 40 ADR decisions with SUPERSEDES chains."""
        self.decisions = generate_decisions()

    def build_planted_conflicts_and_seed_docs(self) -> None:
        """Builds the 14 planted conflicts and their corresponding documents / messages."""
        self.planted_conflicts.clear()
        sys_map = {s.id: s for s in self.systems}

        # ── 1. DIRECT CONFLICTS (5) ───────────────────────────────────────────
        # Plant 1: Carrier invoice dispute window
        doc1 = DocumentData(
            id="doc-0001",
            title="Carrier Billing FAQ",
            path="wiki/carrier-billing/faq.md",
            kind="wiki",
            updated_at=self.base_time + 10_000_000,
            author_id="usr-0032",
            governs_system_ids=["sys-carrier-billing"],
            cites_decision_ids=[],
            factual_sentences=["Carrier invoices can be disputed within 30 days of delivery."],
        )
        doc2 = DocumentData(
            id="doc-0002",
            title="Finance Ops: Month-End Close",
            path="runbooks/finance/month-end-close.md",
            kind="runbook",
            updated_at=self.base_time + 8_000_000,
            author_id="usr-0031",
            governs_system_ids=["sys-finance-ledger", "sys-carrier-billing"],
            cites_decision_ids=["dec-0015"],
            factual_sentences=["The dispute window for carrier invoices is 45 days from the invoice date."],
        )
        ra_1 = compute_blast_radius([sys_map[sid] for sid in doc1.governs_system_ids], 1, len(doc1.cites_decision_ids))
        rb_1 = compute_blast_radius([sys_map[sid] for sid in doc2.governs_system_ids], 1, len(doc2.cites_decision_ids))
        self.planted_conflicts.append(PlantedConflictData(
            id="plant-01",
            kind="direct",
            entity_slug="carrier-invoice-dispute-window",
            predicate="dispute_window",
            source_a_id=doc1.id,
            source_b_id=doc2.id,
            evidence_span_a="Carrier invoices can be disputed within 30 days of delivery.",
            evidence_span_b="The dispute window for carrier invoices is 45 days from the invoice date.",
            correct_side="b",
            rationale="Finance Ops Month-End Close policy defines the dispute window for financial settlement.",
            expected_blast_radius=max(ra_1, rb_1),
            side_a_blast_radius=ra_1,
            side_b_blast_radius=rb_1,
            governed_systems=list(set(doc1.governs_system_ids + doc2.governs_system_ids)),
            doc_count=2,
            citing_decisions=1,
        ))

        # Plant 2: Warehouse A-Class cycle count frequency
        doc3 = DocumentData(
            id="doc-0003",
            title="WMS Operations Guide",
            path="wiki/warehouse/wms-operations.md",
            kind="wiki",
            updated_at=self.base_time + 5_000_000,
            author_id="usr-0017",
            governs_system_ids=["sys-warehouse-wms"],
            cites_decision_ids=[],
            factual_sentences=["Cycle counts run nightly for A-class SKUs."],
        )
        doc4 = DocumentData(
            id="doc-0004",
            title="Inventory Accuracy Standard",
            path="specs/warehouse/inventory-accuracy.md",
            kind="spec",
            updated_at=self.base_time + 6_000_000,
            author_id="usr-0018",
            governs_system_ids=["sys-warehouse-wms", "sys-inventory-service"],
            cites_decision_ids=["dec-0077"],
            factual_sentences=["A-class SKUs are cycle counted weekly."],
        )
        ra_2 = compute_blast_radius([sys_map[sid] for sid in doc3.governs_system_ids], 1, len(doc3.cites_decision_ids))
        rb_2 = compute_blast_radius([sys_map[sid] for sid in doc4.governs_system_ids], 1, len(doc4.cites_decision_ids))
        self.planted_conflicts.append(PlantedConflictData(
            id="plant-02",
            kind="direct",
            entity_slug="a-class-cycle-count",
            predicate="cycle_count_frequency",
            source_a_id=doc3.id,
            source_b_id=doc4.id,
            evidence_span_a="Cycle counts run nightly for A-class SKUs.",
            evidence_span_b="A-class SKUs are cycle counted weekly.",
            correct_side="b",
            rationale="Inventory Accuracy Standard cites accepted ADR-77 for distribution center counting.",
            expected_blast_radius=max(ra_2, rb_2),
            side_a_blast_radius=ra_2,
            side_b_blast_radius=rb_2,
            governed_systems=list(set(doc3.governs_system_ids + doc4.governs_system_ids)),
            doc_count=2,
            citing_decisions=1,
        ))

        # Plant 3: Proof of delivery customer signature
        doc5 = DocumentData(
            id="doc-0005",
            title="Driver App README",
            path="repos/driver-app/README.md",
            kind="readme",
            updated_at=self.base_time + 12_000_000,
            author_id="usr-0042",
            governs_system_ids=["sys-driver-app"],
            cites_decision_ids=[],
            factual_sentences=["Proof of delivery customer signature is optional since v4.2."],
        )
        doc6 = DocumentData(
            id="doc-0006",
            title="Fleet Safety Policy",
            path="specs/fleet/safety-policy.md",
            kind="spec",
            updated_at=self.base_time + 11_000_000,
            author_id="usr-0040",
            governs_system_ids=["sys-driver-app", "sys-fleet-telematics"],
            cites_decision_ids=["dec-0073"],
            factual_sentences=["Proof of delivery customer signature is strictly mandatory for every drop-off."],
        )
        ra_3 = compute_blast_radius([sys_map[sid] for sid in doc5.governs_system_ids], 1, len(doc5.cites_decision_ids))
        rb_3 = compute_blast_radius([sys_map[sid] for sid in doc6.governs_system_ids], 1, len(doc6.cites_decision_ids))
        self.planted_conflicts.append(PlantedConflictData(
            id="plant-03",
            kind="direct",
            entity_slug="proof-of-delivery",
            predicate="signature_required",
            source_a_id=doc5.id,
            source_b_id=doc6.id,
            evidence_span_a="Proof of delivery customer signature is optional since v4.2.",
            evidence_span_b="Proof of delivery customer signature is strictly mandatory for every drop-off.",
            correct_side="b",
            rationale="Fleet Safety Policy governs legal compliance for cargo delivery.",
            expected_blast_radius=max(ra_3, rb_3),
            side_a_blast_radius=ra_3,
            side_b_blast_radius=rb_3,
            governed_systems=list(set(doc5.governs_system_ids + doc6.governs_system_ids)),
            doc_count=2,
            citing_decisions=1,
        ))

        # Plant 4: On-call tier 1 ack SLA (Touches ALL 5 Tier 1 systems! Highest blast radius!)
        doc7 = DocumentData(
            id="doc-0007",
            title="Platform On-call Rotation Guide",
            path="runbooks/oncall/rotation.md",
            kind="runbook",
            updated_at=self.base_time + 4_000_000,
            author_id="usr-0002",
            governs_system_ids=[
                "sys-dispatch-router",
                "sys-warehouse-wms",
                "sys-cold-chain-monitor",
                "sys-finance-ledger",
                "sys-payments-gateway",
            ],
            cites_decision_ids=["dec-0047"],
            factual_sentences=["Tier 1 systems have a 15 minute acknowledgement target for on-call engineers."],
        )
        doc8 = DocumentData(
            id="doc-0008",
            title="Core Services Escalation SOP",
            path="runbooks/infra/escalation-sop.md",
            kind="runbook",
            updated_at=self.base_time + 4_500_000,
            author_id="usr-0001",
            governs_system_ids=["sys-dispatch-router", "sys-payments-gateway"],
            cites_decision_ids=[],
            factual_sentences=["Tier 1 systems have a 5 minute acknowledgement target for on-call engineers."],
        )
        ra_4 = compute_blast_radius([sys_map[sid] for sid in doc7.governs_system_ids], 1, len(doc7.cites_decision_ids))
        rb_4 = compute_blast_radius([sys_map[sid] for sid in doc8.governs_system_ids], 1, len(doc8.cites_decision_ids))
        self.planted_conflicts.append(PlantedConflictData(
            id="plant-04",
            kind="direct",
            entity_slug="oncall-tier1-ack",
            predicate="oncall_ack_target",
            source_a_id=doc7.id,
            source_b_id=doc8.id,
            evidence_span_a="Tier 1 systems have a 15 minute acknowledgement target for on-call engineers.",
            evidence_span_b="Tier 1 systems have a 5 minute acknowledgement target for on-call engineers.",
            correct_side="a",
            rationale="Platform On-call Rotation Guide reflects agreed platform incident management policy.",
            expected_blast_radius=max(ra_4, rb_4),
            side_a_blast_radius=ra_4,
            side_b_blast_radius=rb_4,
            governed_systems=list(set(doc7.governs_system_ids + doc8.governs_system_ids)),
            doc_count=2,
            citing_decisions=1,
        ))

        # Plant 5: Customer damage claim auto-approval threshold (Governs 0 systems! Low blast radius!)
        doc9 = DocumentData(
            id="doc-0009",
            title="Returns and Damage Claims Process",
            path="wiki/customer-ops/returns-and-claims.md",
            kind="wiki",
            updated_at=self.base_time + 3_000_000,
            author_id="usr-0056",
            governs_system_ids=[],
            cites_decision_ids=[],
            factual_sentences=["Customer damage claims under 250 USD are approved automatically without human review."],
        )
        doc10 = DocumentData(
            id="doc-0010",
            title="Customer Ops Authority Matrix",
            path="specs/customer-ops/authority-matrix.md",
            kind="spec",
            updated_at=self.base_time + 3_500_000,
            author_id="usr-0054",
            governs_system_ids=[],
            cites_decision_ids=["dec-0087"],
            factual_sentences=["Customer damage claims under 400 USD are approved automatically without human review."],
        )
        ra_5 = compute_blast_radius([sys_map[sid] for sid in doc9.governs_system_ids], 1, len(doc9.cites_decision_ids))
        rb_5 = compute_blast_radius([sys_map[sid] for sid in doc10.governs_system_ids], 1, len(doc10.cites_decision_ids))
        self.planted_conflicts.append(PlantedConflictData(
            id="plant-05",
            kind="direct",
            entity_slug="damage-claim-auto-approval",
            predicate="refund_auto_approval_limit",
            source_a_id=doc9.id,
            source_b_id=doc10.id,
            evidence_span_a="Customer damage claims under 250 USD are approved automatically without human review.",
            evidence_span_b="Customer damage claims under 400 USD are approved automatically without human review.",
            correct_side="b",
            rationale="Authority Matrix reflects latest financial authorization thresholds under ADR-87.",
            expected_blast_radius=max(ra_5, rb_5),
            side_a_blast_radius=ra_5,
            side_b_blast_radius=rb_5,
            governed_systems=[],
            doc_count=2,
            citing_decisions=1,
        ))

        # ── 2. SUPERSEDED CONFLICTS (5) ───────────────────────────────────────
        # Plant 6: Reefer excursion limit (Demo Case 2)
        # ADR-88 (decided_at ~1742000000) supersedes ADR-63 supersedes ADR-41 (dec-0041).
        # doc11 asserts ADR-41's 30 mins, but updated_at is 1780000000 (NEWER than ADR-88 decided_at).
        doc11 = DocumentData(
            id="doc-0011",
            title="Cold Chain Excursion Runbook",
            path="runbooks/cold-chain/excursion-response.md",
            kind="runbook",
            updated_at=1780000000,
            author_id="usr-0024",
            governs_system_ids=["sys-cold-chain-monitor", "sys-warehouse-wms", "sys-fleet-telematics"],
            cites_decision_ids=["dec-0041"],
            factual_sentences=["Reefer loads that stay above 8 degrees C for more than 30 minutes are rejected at the receiving dock."],
        )
        doc12 = DocumentData(
            id="doc-0012",
            title="Cold Chain Policy v3",
            path="specs/cold-chain/policy-v3.md",
            kind="spec",
            updated_at=1743000000,
            author_id="usr-0024",
            governs_system_ids=["sys-cold-chain-monitor"],
            cites_decision_ids=["dec-0088"],
            factual_sentences=["A reefer load is rejected once it has spent 15 minutes above 8 degrees C at any point after pickup."],
        )
        ra_6 = compute_blast_radius([sys_map[sid] for sid in doc11.governs_system_ids], 1, len(doc11.cites_decision_ids))
        rb_6 = compute_blast_radius([sys_map[sid] for sid in doc12.governs_system_ids], 1, len(doc12.cites_decision_ids))
        self.planted_conflicts.append(PlantedConflictData(
            id="plant-06",
            kind="superseded",
            entity_slug="reefer-excursion-limit",
            predicate="excursion_tolerance_duration",
            source_a_id=doc11.id,
            source_b_id=doc12.id,
            evidence_span_a="Reefer loads that stay above 8 degrees C for more than 30 minutes are rejected at the receiving dock.",
            evidence_span_b="A reefer load is rejected once it has spent 15 minutes above 8 degrees C at any point after pickup.",
            correct_side="b",
            rationale="ADR-88 supersedes ADR-41; traversal walks SUPERSEDES backwards to accept the 15-minute standard.",
            expected_blast_radius=max(ra_6, rb_6),
            side_a_blast_radius=ra_6,
            side_b_blast_radius=rb_6,
            governed_systems=list(set(doc11.governs_system_ids + doc12.governs_system_ids)),
            doc_count=2,
            citing_decisions=2,
        ))

        # Plant 7: Driver shift driving hours
        # ADR-74 supersedes ADR-30 (dec-0030). doc13 updated_at is newer than ADR-74 decided_at.
        doc13 = DocumentData(
            id="doc-0013",
            title="Driver App Operations README",
            path="repos/driver-app/operations.md",
            kind="readme",
            updated_at=1775000000,
            author_id="usr-0042",
            governs_system_ids=["sys-driver-app"],
            cites_decision_ids=["dec-0030"],
            factual_sentences=["Drivers are blocked from accepting new loads after 11 hours of driving in a shift."],
        )
        doc14 = DocumentData(
            id="doc-0014",
            title="Fleet Safety Standard",
            path="specs/fleet/driver-safety.md",
            kind="spec",
            updated_at=1738000000,
            author_id="usr-0040",
            governs_system_ids=["sys-driver-app", "sys-fleet-telematics"],
            cites_decision_ids=["dec-0074"],
            factual_sentences=["No driver may drive more than 10 hours in a shift across all lanes."],
        )
        ra_7 = compute_blast_radius([sys_map[sid] for sid in doc13.governs_system_ids], 1, len(doc13.cites_decision_ids))
        rb_7 = compute_blast_radius([sys_map[sid] for sid in doc14.governs_system_ids], 1, len(doc14.cites_decision_ids))
        self.planted_conflicts.append(PlantedConflictData(
            id="plant-07",
            kind="superseded",
            entity_slug="driver-hours-limit",
            predicate="driving_hours_limit",
            source_a_id=doc13.id,
            source_b_id=doc14.id,
            evidence_span_a="Drivers are blocked from accepting new loads after 11 hours of driving in a shift.",
            evidence_span_b="No driver may drive more than 10 hours in a shift across all lanes.",
            correct_side="b",
            rationale="ADR-74 supersedes ADR-30; the 10-hour ceiling is the legally active safety rule.",
            expected_blast_radius=max(ra_7, rb_7),
            side_a_blast_radius=ra_7,
            side_b_blast_radius=rb_7,
            governed_systems=list(set(doc13.governs_system_ids + doc14.governs_system_ids)),
            doc_count=2,
            citing_decisions=2,
        ))

        # Plant 8: Dispatch router external solver retry attempts
        # ADR-52 supersedes ADR-35 supersedes ADR-18 (dec-0018).
        doc15 = DocumentData(
            id="doc-0015",
            title="Dispatch Router Solver Runbook",
            path="runbooks/dispatch/solver-troubleshooting.md",
            kind="runbook",
            updated_at=1782000000,
            author_id="usr-0009",
            governs_system_ids=["sys-dispatch-router"],
            cites_decision_ids=["dec-0018"],
            factual_sentences=["External routing solver calls are retried up to 3 times before fallback."],
        )
        doc16 = DocumentData(
            id="doc-0016",
            title="Dispatch Engine Service Architecture",
            path="specs/dispatch/engine-architecture.md",
            kind="spec",
            updated_at=1745000000,
            author_id="usr-0009",
            governs_system_ids=["sys-dispatch-router", "sys-tracking-api"],
            cites_decision_ids=["dec-0052"],
            factual_sentences=["External routing solver calls are retried exactly 1 time to prevent cascade timeouts."],
        )
        ra_8 = compute_blast_radius([sys_map[sid] for sid in doc15.governs_system_ids], 1, len(doc15.cites_decision_ids))
        rb_8 = compute_blast_radius([sys_map[sid] for sid in doc16.governs_system_ids], 1, len(doc16.cites_decision_ids))
        self.planted_conflicts.append(PlantedConflictData(
            id="plant-08",
            kind="superseded",
            entity_slug="dispatch-router-retry-limit",
            predicate="retry_policy",
            source_a_id=doc15.id,
            source_b_id=doc16.id,
            evidence_span_a="External routing solver calls are retried up to 3 times before fallback.",
            evidence_span_b="External routing solver calls are retried exactly 1 time to prevent cascade timeouts.",
            correct_side="b",
            rationale="ADR-52 supersedes ADR-18; single retry prevents downstream cascading queue delays.",
            expected_blast_radius=max(ra_8, rb_8),
            side_a_blast_radius=ra_8,
            side_b_blast_radius=rb_8,
            governed_systems=list(set(doc15.governs_system_ids + doc16.governs_system_ids)),
            doc_count=2,
            citing_decisions=2,
        ))

        # Plant 9: Warehouse dock arrival grace period
        # ADR-68 supersedes ADR-22 (dec-0022).
        doc17 = DocumentData(
            id="doc-0017",
            title="Warehouse Dock Scheduling Runbook",
            path="runbooks/warehouse/dock-scheduling.md",
            kind="runbook",
            updated_at=1785000000,
            author_id="usr-0017",
            governs_system_ids=["sys-warehouse-wms", "sys-depot-kiosk"],
            cites_decision_ids=["dec-0022"],
            factual_sentences=["Carriers arriving within 60 minutes of scheduled slot retain dock priority."],
        )
        doc18 = DocumentData(
            id="doc-0018",
            title="Distribution Center Gate Operations",
            path="specs/warehouse/gate-operations.md",
            kind="spec",
            updated_at=1740000000,
            author_id="usr-0017",
            governs_system_ids=["sys-warehouse-wms"],
            cites_decision_ids=["dec-0068"],
            factual_sentences=["Carriers arriving more than 30 minutes late lose dock appointment and are rescheduled."],
        )
        ra_9 = compute_blast_radius([sys_map[sid] for sid in doc17.governs_system_ids], 1, len(doc17.cites_decision_ids))
        rb_9 = compute_blast_radius([sys_map[sid] for sid in doc18.governs_system_ids], 1, len(doc18.cites_decision_ids))
        self.planted_conflicts.append(PlantedConflictData(
            id="plant-09",
            kind="superseded",
            entity_slug="dock-late-cancellation-window",
            predicate="dock_arrival_tolerance",
            source_a_id=doc17.id,
            source_b_id=doc18.id,
            evidence_span_a="Carriers arriving within 60 minutes of scheduled slot retain dock priority.",
            evidence_span_b="Carriers arriving more than 30 minutes late lose dock appointment and are rescheduled.",
            correct_side="b",
            rationale="ADR-68 supersedes ADR-22; tightened grace period reduces yard congestion.",
            expected_blast_radius=max(ra_9, rb_9),
            side_a_blast_radius=ra_9,
            side_b_blast_radius=rb_9,
            governed_systems=list(set(doc17.governs_system_ids + doc18.governs_system_ids)),
            doc_count=2,
            citing_decisions=2,
        ))

        # Plant 10: Fleet telematics GPS moving ping interval
        # ADR-49 supersedes ADR-12 (dec-0012).
        doc19 = DocumentData(
            id="doc-0019",
            title="Fleet Telematics Data Ingest SOP",
            path="runbooks/fleet/telematics-ingest.md",
            kind="runbook",
            updated_at=1778000000,
            author_id="usr-0039",
            governs_system_ids=["sys-fleet-telematics"],
            cites_decision_ids=["dec-0012"],
            factual_sentences=["Tractors transmit GPS telematics ping every 15 seconds while moving."],
        )
        doc20 = DocumentData(
            id="doc-0020",
            title="Fleet Telematics Ingest README",
            path="repos/fleet-telematics/README.md",
            kind="readme",
            updated_at=1732000000,
            author_id="usr-0039",
            governs_system_ids=["sys-fleet-telematics", "sys-driver-app"],
            cites_decision_ids=["dec-0049"],
            factual_sentences=["Tractors transmit GPS telematics ping every 30 seconds while moving to conserve cellular bandwidth."],
        )
        ra_10 = compute_blast_radius([sys_map[sid] for sid in doc19.governs_system_ids], 1, len(doc19.cites_decision_ids))
        rb_10 = compute_blast_radius([sys_map[sid] for sid in doc20.governs_system_ids], 1, len(doc20.cites_decision_ids))
        self.planted_conflicts.append(PlantedConflictData(
            id="plant-10",
            kind="superseded",
            entity_slug="gps-moving-ping-interval",
            predicate="gps_ping_interval",
            source_a_id=doc19.id,
            source_b_id=doc20.id,
            evidence_span_a="Tractors transmit GPS telematics ping every 15 seconds while moving.",
            evidence_span_b="Tractors transmit GPS telematics ping every 30 seconds while moving to conserve cellular bandwidth.",
            correct_side="b",
            rationale="ADR-49 supersedes ADR-12; 30-second interval balances tracking fidelity and cellular data cost.",
            expected_blast_radius=max(ra_10, rb_10),
            side_a_blast_radius=ra_10,
            side_b_blast_radius=rb_10,
            governed_systems=list(set(doc19.governs_system_ids + doc20.governs_system_ids)),
            doc_count=2,
            citing_decisions=2,
        ))

        # ── 3. UNDOCUMENTED CONFLICTS (4) ─────────────────────────────────────
        # Plant 11: Dispatch router timeout and manual fallback
        doc21 = DocumentData(
            id="doc-0021",
            title="Dispatch Router Failover Runbook",
            path="runbooks/dispatch/router-failover.md",
            kind="runbook",
            updated_at=self.base_time + 7_000_000,
            author_id="usr-0009",
            governs_system_ids=["sys-dispatch-router"],
            cites_decision_ids=["dec-0084"],
            factual_sentences=["If the routing API does not respond within 10 seconds, Dispatch Router falls back to manual dispatch."],
        )
        msg101 = MessageData(
            id="msg-0000101",
            channel="#dispatch-oncall",
            text="We cut the router timeout to 4 seconds last sprint and it now retries on the backup solver automatically without manual dispatch fallback.",
            sent_at=self.base_time + 15_000_000,
            author_id="usr-0009",
        )
        ra_11 = compute_blast_radius([sys_map[sid] for sid in doc21.governs_system_ids], 1, len(doc21.cites_decision_ids))
        rb_11 = compute_blast_radius([], 1, 0)
        self.planted_conflicts.append(PlantedConflictData(
            id="plant-11",
            kind="undocumented",
            entity_slug="dispatch-router",
            predicate="timeout_duration",
            source_a_id=doc21.id,
            source_b_id=msg101.id,
            evidence_span_a="If the routing API does not respond within 10 seconds, Dispatch Router falls back to manual dispatch.",
            evidence_span_b="We cut the router timeout to 4 seconds last sprint and it now retries on the backup solver automatically without manual dispatch fallback.",
            correct_side="b",
            rationale="Operational chat consensus records production change to 4s automated fallback without manual console.",
            expected_blast_radius=max(ra_11, rb_11),
            side_a_blast_radius=ra_11,
            side_b_blast_radius=rb_11,
            governed_systems=doc21.governs_system_ids,
            doc_count=2,
            citing_decisions=1,
        ))

        # Plant 12: Customs Gateway automatic import filing
        doc22 = DocumentData(
            id="doc-0022",
            title="Customs Gateway Integration Spec",
            path="specs/customs/gateway-integration.md",
            kind="spec",
            updated_at=self.base_time + 6_000_000,
            author_id="usr-0047",
            governs_system_ids=["sys-customs-gateway", "sys-dispatch-router"],
            cites_decision_ids=["dec-0038"],
            factual_sentences=["Customs Gateway files import declarations automatically 24 hours before scheduled arrival."],
        )
        msg102 = MessageData(
            id="msg-0000102",
            channel="#customs-brokerage",
            text="Gateway auto-filing has been switched off since August and brokerage is filing declarations manually.",
            sent_at=self.base_time + 15_500_000,
            author_id="usr-0047",
        )
        ra_12 = compute_blast_radius([sys_map[sid] for sid in doc22.governs_system_ids], 1, len(doc22.cites_decision_ids))
        rb_12 = compute_blast_radius([], 1, 0)
        self.planted_conflicts.append(PlantedConflictData(
            id="plant-12",
            kind="undocumented",
            entity_slug="customs-gateway",
            predicate="declaration_filing_lead_time",
            source_a_id=doc22.id,
            source_b_id=msg102.id,
            evidence_span_a="Customs Gateway files import declarations automatically 24 hours before scheduled arrival.",
            evidence_span_b="Gateway auto-filing has been switched off since August and brokerage is filing declarations manually.",
            correct_side="b",
            rationale="Brokerage team chat confirms automated filing disabled following certificate expiration.",
            expected_blast_radius=max(ra_12, rb_12),
            side_a_blast_radius=ra_12,
            side_b_blast_radius=rb_12,
            governed_systems=doc22.governs_system_ids,
            doc_count=2,
            citing_decisions=1,
        ))

        # Plant 13: Payments settlement idempotency retention
        doc23 = DocumentData(
            id="doc-0023",
            title="Payments Gateway Operations Manual",
            path="runbooks/payments/gateway-ops.md",
            kind="runbook",
            updated_at=self.base_time + 8_500_000,
            author_id="usr-0035",
            governs_system_ids=["sys-payments-gateway", "sys-finance-ledger"],
            cites_decision_ids=["dec-0056"],
            factual_sentences=["Payments Gateway caches settlement idempotency keys for 24 hours."],
        )
        msg103 = MessageData(
            id="msg-0000103",
            channel="#payments",
            text="Payment idempotency key retention was increased to 72 hours following the double-charge incident.",
            sent_at=self.base_time + 16_000_000,
            author_id="usr-0035",
        )
        ra_13 = compute_blast_radius([sys_map[sid] for sid in doc23.governs_system_ids], 1, len(doc23.cites_decision_ids))
        rb_13 = compute_blast_radius([], 1, 0)
        self.planted_conflicts.append(PlantedConflictData(
            id="plant-13",
            kind="undocumented",
            entity_slug="payments-gateway",
            predicate="idempotency_window",
            source_a_id=doc23.id,
            source_b_id=msg103.id,
            evidence_span_a="Payments Gateway caches settlement idempotency keys for 24 hours.",
            evidence_span_b="Payment idempotency key retention was increased to 72 hours following the double-charge incident.",
            correct_side="b",
            rationale="Urgent engineering chat hotfix extended payment key retention to 72 hours.",
            expected_blast_radius=max(ra_13, rb_13),
            side_a_blast_radius=ra_13,
            side_b_blast_radius=rb_13,
            governed_systems=doc23.governs_system_ids,
            doc_count=2,
            citing_decisions=1,
        ))

        # Plant 14: Cold chain temperature probe calibration variance tolerance
        doc24 = DocumentData(
            id="doc-0024",
            title="Reefer Temperature Calibration Protocol",
            path="runbooks/cold-chain/probe-calibration.md",
            kind="runbook",
            updated_at=self.base_time + 5_500_000,
            author_id="usr-0027",
            governs_system_ids=["sys-cold-chain-monitor"],
            cites_decision_ids=[],
            factual_sentences=["If the primary reefer probe and secondary logger disagree by more than 1.5 degrees C, open a hardware ticket."],
        )
        msg104 = MessageData(
            id="msg-0000104",
            channel="#cold-chain-ops",
            text="Reefer probe calibration tolerance was tightened to 0.5 degrees C following the dairy shipment audit.",
            sent_at=self.base_time + 16_500_000,
            author_id="usr-0024",
        )
        ra_14 = compute_blast_radius([sys_map[sid] for sid in doc24.governs_system_ids], 1, len(doc24.cites_decision_ids))
        rb_14 = compute_blast_radius([], 1, 0)
        self.planted_conflicts.append(PlantedConflictData(
            id="plant-14",
            kind="undocumented",
            entity_slug="cold-chain-monitor",
            predicate="probe_calibration_tolerance",
            source_a_id=doc24.id,
            source_b_id=msg104.id,
            evidence_span_a="If the primary reefer probe and secondary logger disagree by more than 1.5 degrees C, open a hardware ticket.",
            evidence_span_b="Reefer probe calibration tolerance was tightened to 0.5 degrees C following the dairy shipment audit.",
            correct_side="b",
            rationale="Quality audit in chat tightened variance threshold to 0.5 degrees C.",
            expected_blast_radius=max(ra_14, rb_14),
            side_a_blast_radius=ra_14,
            side_b_blast_radius=rb_14,
            governed_systems=doc24.governs_system_ids,
            doc_count=2,
            citing_decisions=0,
        ))

        # Add the 24 initial documents
        self.documents = [
            doc1, doc2, doc3, doc4, doc5, doc6, doc7, doc8, doc9, doc10,
            doc11, doc12, doc13, doc14, doc15, doc16, doc17, doc18, doc19, doc20,
            doc21, doc22, doc23, doc24,
        ]

        # Add the 4 special messages (stored for message generation)
        self.special_messages = [msg101, msg102, msg103, msg104]

    def build_remaining_documents(self) -> None:
        """Expands the document set up to exactly 312 documents with extractable facts."""
        kinds_cycle = ["runbook", "wiki", "spec", "readme"]
        system_ids = [s.id for s in self.systems]
        author_ids = [p.id for p in self.people]
        decision_ids = [d.id for d in self.decisions]

        # Templates for generating extractable factual sentences on single unbroken lines
        fact_templates = [
            ("retry_policy", "{subj} retries failed external requests up to {n} times with backoff."),
            ("timeout_duration", "Requests to {subj} timeout after {n} milliseconds."),
            ("cycle_count_frequency", "{subj} requires inventory cycle count verification every {n} days."),
            ("audit_retention_period", "Transaction logs for {subj} are archived for {n} days."),
            ("oncall_ack_target", "On-call engineers for {subj} must acknowledge critical alerts within {n} minutes."),
            ("backup_frequency", "Automated snapshots for {subj} are taken every {n} hours."),
            ("reconciliation_frequency", "Ledger entries in {subj} are reconciled every {n} hours."),
            ("temperature_threshold", "High priority containers in {subj} must maintain a temperature below {n} degrees C."),
            ("gps_ping_interval", "Units tracked by {subj} report telemetry every {n} seconds."),
            ("dispute_window", "Customer dispute notices for {subj} must be filed within {n} days of delivery."),
        ]

        curr_id = len(self.documents) + 1
        while len(self.documents) < 312:
            doc_id = f"doc-{curr_id:04d}"
            kind = kinds_cycle[(curr_id - 1) % len(kinds_cycle)]
            author_id = self.rng.choice(author_ids)
            
            # Select 0 to 2 governed systems deterministically
            num_gov = self.rng.choice([0, 1, 1, 2])
            gov_systems = self.rng.sample(system_ids, k=num_gov) if num_gov > 0 else []
            
            # Select 0 to 1 cited decisions
            has_cite = self.rng.random() < 0.35
            cites = [self.rng.choice(decision_ids)] if has_cite else []

            # Determine subject and aliases
            primary_sys = gov_systems[0] if gov_systems else self.rng.choice(system_ids)
            sys_obj = next(s for s in self.systems if s.id == primary_sys)
            aliases = SUBJECT_ALIASES.get(sys_obj.slug, [sys_obj.name])
            subj_name = self.rng.choice(aliases)

            # Generate 4 to 6 atomic factual sentences
            num_facts = self.rng.randint(4, 6)
            facts: list[str] = []
            selected_templates = self.rng.sample(fact_templates, k=num_facts)
            for pred, tmpl in selected_templates:
                val = self.rng.choice([2, 3, 5, 10, 15, 30, 60, 90, 180, 365, 1000, 5000])
                fact_line = tmpl.format(subj=subj_name, n=val)
                facts.append(fact_line)

            # Title & Path
            title_prefix = {
                "runbook": "Operations Runbook",
                "wiki": "Architecture Overview",
                "spec": "Technical Specification",
                "readme": "Component README",
            }[kind]
            title = f"{sys_obj.name} {title_prefix} Part {curr_id}"
            folder = {
                "runbook": "runbooks",
                "wiki": "wiki",
                "spec": "specs",
                "readme": "repos",
            }[kind]
            path = f"{folder}/{sys_obj.slug}/{kind}-{curr_id:04d}.md"
            updated_at = self.base_time + (curr_id * 3600 * 12)

            doc = DocumentData(
                id=doc_id,
                title=title,
                path=path,
                kind=kind,
                updated_at=updated_at,
                author_id=author_id,
                governs_system_ids=gov_systems,
                cites_decision_ids=cites,
                factual_sentences=facts,
            )
            self.documents.append(doc)
            curr_id += 1

        # Populate document full text with single unbroken sentence lines
        for doc in self.documents:
            gov_str = f"Governs systems: {', '.join(doc.governs_system_ids)}." if doc.governs_system_ids else "Governs: general organization procedures."
            cite_str = f"Cites architectural decisions: {', '.join(doc.cites_decision_ids)}." if doc.cites_decision_ids else "No external ADR cited."
            intro = f"# {doc.title}\n\nDocument ID: {doc.id}. Last updated epoch timestamp: {doc.updated_at}.\n{gov_str}\n{cite_str}\n\n## Procedures and Policies\n"
            body = "\n".join(doc.factual_sentences)
            doc.text = f"{intro}{body}\n"

    def build_tickets(self) -> None:
        """Generates exactly 400 tickets."""
        self.tickets.clear()
        system_ids = [s.id for s in self.systems]

        # Include tickets referencing planted incident details
        planted_tickets = [
            TicketData(
                id="tkt-0001",
                ref="INC-2291",
                title="Reefer load rejected at 18 minutes, carrier disputes chargeback",
                text="Load NW-55812 was rejected at dock 3 after 18 minutes above 8 degrees C. The carrier disputes the chargeback and cites the 30 minute limit in the excursion runbook. Policy v3 says 15 minutes; chargeback upheld.",
                state="closed",
                closed_at=self.base_time + 14_000_000,
                system_id="sys-cold-chain-monitor",
            ),
            TicketData(
                id="tkt-0002",
                ref="INC-3410",
                title="Cold chain probe temperature variance alert during dairy transit",
                text="Reefer probe calibration tolerance was tightened to 0.5 degrees C following the dairy shipment audit. The probe drift exceeded 0.8 degrees C and triggered trailer sensor replacement.",
                state="closed",
                closed_at=self.base_time + 16_600_000,
                system_id="sys-cold-chain-monitor",
            ),
        ]
        self.tickets.extend(planted_tickets)

        ticket_titles = [
            "Replication lag exceeded threshold during morning peak",
            "Solver timeout during bulk route recalculation",
            "Missing accessorial fee in carrier EDI transmission",
            "Handheld scanner barcode reconciliation failure in aisle 4",
            "Cross-border declaration pre-arrival filing validation error",
            "Idempotency cache eviction causing duplicate charge warning",
            "Driver app GPS telemetry stream disconnected on interstate 80",
            "Dock gate appointment rescheduled after 45 minute arrival delay",
            "Cold chain secondary probe failed automated CRC checksum",
            "Carrier billing invoice dispute window expired without review",
        ]

        states = ["closed", "closed", "closed", "open", "in-progress"]

        for i in range(len(self.tickets) + 1, 401):
            tkt_id = f"tkt-{i:04d}"
            ref = f"INC-{1000 + i}"
            title = f"{self.rng.choice(ticket_titles)} (Unit {i})"
            sys_id = self.rng.choice(system_ids)
            sys_obj = next(s for s in self.systems if s.id == sys_id)
            state = self.rng.choice(states)
            closed_at = (self.base_time + i * 20000) if state == "closed" else None
            text = (
                f"Incident report for {sys_obj.name}. "
                f"Automated monitoring alerted on anomaly. "
                f"Assigned on-call engineer responded. Status is {state}."
            )
            self.tickets.append(TicketData(
                id=tkt_id,
                ref=ref,
                title=title,
                text=text,
                state=state,
                closed_at=closed_at,
                system_id=sys_id,
            ))

    def build_messages(self) -> None:
        """Generates exactly 2,000 chat messages across channels."""
        self.messages.clear()
        author_ids = [p.id for p in self.people]

        # Reserve the 4 special planted messages
        special_map = {m.id: m for m in self.special_messages}

        chat_templates = [
            "deploying hotfix for {sys} solver to production cluster",
            "heads up: oncall handover completed for {chan} queue",
            "investigating elevated latency on {sys} read endpoints",
            "carrier billing reconciliation completed for yesterday wave",
            "reminder: cycle count audit scheduled for warehouse zone B",
            "reefer telemetry looks nominal across all active midwest loads",
            "database snapshot for {sys} finished in 14 seconds",
            "dispatch solver fallback test passed in staging environment",
            "pre-trip inspections verified for morning fleet departure",
            "customs EDI gateway processed 450 declarations in last hour",
        ]

        for i in range(1, 2001):
            msg_id = f"msg-{i:07d}"
            if msg_id in special_map:
                self.messages.append(special_map[msg_id])
                continue

            chan = self.rng.choice(CHANNELS)
            sys_obj = self.rng.choice(self.systems)
            author = self.rng.choice(author_ids)
            tmpl = self.rng.choice(chat_templates)
            text = tmpl.format(sys=sys_obj.name, chan=chan)
            sent_at = self.base_time + (i * 1200)

            self.messages.append(MessageData(
                id=msg_id,
                channel=chan,
                text=text,
                sent_at=sent_at,
                author_id=author,
            ))

    def generate_all(self) -> None:
        """Runs the complete deterministic generation pipeline."""
        self.build_people()
        self.build_systems()
        self.build_decisions()
        self.build_planted_conflicts_and_seed_docs()
        self.build_remaining_documents()
        self.build_tickets()
        self.build_messages()

    def write_corpus(self, out_dir: Path) -> None:
        """Writes corpus markdown files, JSONL files, unified JSON corpus, ground_truth.json, and Cypher seed."""
        corpus_dir = out_dir / "corpus"
        docs_dir = corpus_dir / "docs"
        adr_dir = corpus_dir / "adr"
        docs_dir.mkdir(parents=True, exist_ok=True)
        adr_dir.mkdir(parents=True, exist_ok=True)

        # 1. Write document markdown files
        for doc in self.documents:
            file_path = docs_dir / f"{doc.id}.md"
            file_path.write_text(doc.text, encoding="utf-8")

        # 2. Write ADR markdown files
        for dec in self.decisions:
            file_path = adr_dir / f"{dec.ref}.md"
            content = f"# {dec.title}\n\nReference: {dec.ref}\nID: {dec.id}\nDecided Epoch: {dec.decided_at}\n\n{dec.text}\n"
            file_path.write_text(content, encoding="utf-8")

        # 3. Write tickets JSONL
        tickets_file = corpus_dir / "tickets.jsonl"
        with tickets_file.open("w", encoding="utf-8") as f:
            for tkt in self.tickets:
                data = {
                    "id": tkt.id,
                    "ref": tkt.ref,
                    "title": tkt.title,
                    "text": tkt.text,
                    "state": tkt.state,
                    "closed_at": tkt.closed_at,
                    "system_id": tkt.system_id,
                }
                f.write(json.dumps(data) + "\n")

        # 4. Write messages JSONL
        messages_file = corpus_dir / "messages.jsonl"
        with messages_file.open("w", encoding="utf-8") as f:
            for msg in self.messages:
                data = {
                    "id": msg.id,
                    "channel": msg.channel,
                    "text": msg.text,
                    "sent_at": msg.sent_at,
                    "author_id": msg.author_id,
                }
                f.write(json.dumps(data) + "\n")

        # 5. Write unified corpus.json (matching mini-corpus.json schema)
        unified = {
            "documents": [
                {
                    "id": d.id,
                    "title": d.title,
                    "path": d.path,
                    "kind": d.kind,
                    "updated_at": d.updated_at,
                    "text": d.text,
                }
                for d in self.documents
            ],
            "messages": [
                {
                    "id": m.id,
                    "channel": m.channel,
                    "sent_at": m.sent_at,
                    "text": m.text,
                }
                for m in self.messages
            ],
            "tickets": [
                {
                    "id": t.id,
                    "ref": t.ref,
                    "title": t.title,
                    "text": t.text,
                    "state": t.state,
                    "closed_at": t.closed_at,
                }
                for t in self.tickets
            ],
            "planted_contradictions": [
                {
                    "id": p.id,
                    "kind": p.kind,
                    "subject_ref": p.entity_slug,
                    "predicate": p.predicate,
                    "a": {"source_id": p.source_a_id, "evidence_span": p.evidence_span_a},
                    "b": {"source_id": p.source_b_id, "evidence_span": p.evidence_span_b},
                    "correct_side": p.correct_side,
                    "rationale": p.rationale,
                    "expected_blast_radius": p.expected_blast_radius,
                }
                for p in self.planted_conflicts
            ],
        }
        corpus_json_file = out_dir / "corpus.json"
        corpus_json_file.write_text(json.dumps(unified, indent=2), encoding="utf-8")

        # 6. Write ground_truth.json
        ground_truth_file = out_dir / "ground_truth.json"
        ground_truth_data = {
            "version": "1.0",
            "total_planted": len(self.planted_conflicts),
            "split": {
                "direct": sum(1 for p in self.planted_conflicts if p.kind == "direct"),
                "superseded": sum(1 for p in self.planted_conflicts if p.kind == "superseded"),
                "undocumented": sum(1 for p in self.planted_conflicts if p.kind == "undocumented"),
            },
            "conflicts": [
                {
                    "id": p.id,
                    "kind": p.kind,
                    "entity_slug": p.entity_slug,
                    "predicate": p.predicate,
                    "source_a_id": p.source_a_id,
                    "source_b_id": p.source_b_id,
                    "evidence_span_a": p.evidence_span_a,
                    "evidence_span_b": p.evidence_span_b,
                    "correct_side": p.correct_side,
                    "rationale": p.rationale,
                    "expected_blast_radius": p.expected_blast_radius,
                    "side_a_blast_radius": p.side_a_blast_radius,
                    "side_b_blast_radius": p.side_b_blast_radius,
                    "governed_systems": p.governed_systems,
                }
                for p in self.planted_conflicts
            ],
        }
        ground_truth_file.write_text(json.dumps(ground_truth_data, indent=2), encoding="utf-8")

        # 7. Write graph_seed.cypher (Structural Graph only)
        cypher_file = out_dir / "graph_seed.cypher"
        self._write_cypher_seed(cypher_file)

    def _write_cypher_seed(self, file_path: Path) -> None:
        """Writes raw Cypher commands to build the structural graph (CONTRACT §5)."""
        lines: list[str] = [
            "// Northwind Logistics Structural Graph Seed",
            "// Contains: Person, System, Decision, Document, Ticket, Message",
            "// Edges: AUTHORED, OWNS, GOVERNS, CITES, SUPERSEDES",
            "",
        ]

        # 1. People
        for p in self.people:
            name_esc = p.name.replace("'", "\\'")
            role_esc = p.role.replace("'", "\\'")
            lines.append(f"CREATE (:Person {{id: '{p.id}', name: '{name_esc}', role: '{role_esc}', active: {str(p.active).lower()}}});")

        # 2. Systems
        for s in self.systems:
            name_esc = s.name.replace("'", "\\'")
            lines.append(f"CREATE (:System {{id: '{s.id}', name: '{name_esc}', tier: {s.tier}}});")

        # 3. Decisions
        for d in self.decisions:
            title_esc = d.title.replace("'", "\\'")
            lines.append(f"CREATE (:Decision {{id: '{d.id}', ref: '{d.ref}', title: '{title_esc}', status: '{d.status}', decided_at: {d.decided_at}}});")

        # 4. Documents
        for doc in self.documents:
            title_esc = doc.title.replace("'", "\\'")
            lines.append(f"CREATE (:Document {{id: '{doc.id}', title: '{title_esc}', path: '{doc.path}', kind: '{doc.kind}', updated_at: {doc.updated_at}}});")

        # 5. Tickets
        for tkt in self.tickets:
            title_esc = tkt.title.replace("'", "\\'")
            text_esc = tkt.text.replace("'", "\\'")
            closed_val = tkt.closed_at if tkt.closed_at is not None else "null"
            lines.append(f"CREATE (:Ticket {{id: '{tkt.id}', ref: '{tkt.ref}', title: '{title_esc}', text: '{text_esc}', state: '{tkt.state}', closed_at: {closed_val}}});")

        # 6. Messages
        for msg in self.messages:
            text_esc = msg.text.replace("'", "\\'")
            lines.append(f"CREATE (:Message {{id: '{msg.id}', channel: '{msg.channel}', text: '{text_esc}', sent_at: {msg.sent_at}}});")

        # ── Edges ──
        lines.append("\n// Relationships\n")

        # OWNS: Person -> System
        for s in self.systems:
            lines.append(f"MATCH (p:Person {{id: '{s.owner_id}'}}), (s:System {{id: '{s.id}'}}) CREATE (p)-[:OWNS]->(s);")

        # AUTHORED: Person -> Decision
        for d in self.decisions:
            lines.append(f"MATCH (p:Person {{id: '{d.author_id}'}}), (dec:Decision {{id: '{d.id}'}}) CREATE (p)-[:AUTHORED]->(dec);")

        # SUPERSEDES: Decision -> Decision (newer -> older)
        for d in self.decisions:
            if d.supersedes_id:
                lines.append(f"MATCH (newer:Decision {{id: '{d.id}'}}), (older:Decision {{id: '{d.supersedes_id}'}}) CREATE (newer)-[:SUPERSEDES]->(older);")

        # AUTHORED: Person -> Document
        for doc in self.documents:
            lines.append(f"MATCH (p:Person {{id: '{doc.author_id}'}}), (d:Document {{id: '{doc.id}'}}) CREATE (p)-[:AUTHORED]->(d);")

        # GOVERNS: Document -> System
        for doc in self.documents:
            for sys_id in doc.governs_system_ids:
                lines.append(f"MATCH (d:Document {{id: '{doc.id}'}}), (s:System {{id: '{sys_id}'}}) CREATE (d)-[:GOVERNS]->(s);")

        # CITES: Document -> Decision
        for doc in self.documents:
            for dec_id in doc.cites_decision_ids:
                lines.append(f"MATCH (d:Document {{id: '{doc.id}'}}), (dec:Decision {{id: '{dec_id}'}}) CREATE (d)-[:CITES]->(dec);")

        file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic Northwind Logistics data generator.")
    parser.add_argument("--seed", type=int, default=42, help="Seed for pseudorandom generator (default: 42)")
    parser.add_argument("--out", type=str, default="data/out", help="Output directory path (default: data/out)")
    args = parser.parse_args()

    start_time = time.perf_counter()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    generator = NorthwindGenerator(seed=args.seed)
    generator.generate_all()
    generator.write_corpus(out_dir)
    elapsed = time.perf_counter() - start_time

    # Output statistics per user requirement:
    # "Do NOT tune volumes to hit 1,800 claims or 340 pairs. Print what the generator actually produces (documents, fact sentences, distinct subjects) and nothing more."
    total_facts = sum(len(d.factual_sentences) for d in generator.documents)
    subjects = set(s.slug for s in generator.systems)

    print(f"Generated Northwind Logistics corpus in {elapsed:.3f} s:")
    print(f"  People:            {len(generator.people)} (across {len(TEAMS)} teams)")
    print(f"  Systems:           {len(generator.systems)} (tiers 1-3)")
    print(f"  Decisions (ADRs):  {len(generator.decisions)} (14 chains, depth 2-4)")
    print(f"  Documents:         {len(generator.documents)} (runbooks, wikis, specs, READMEs)")
    print(f"  Fact sentences:    {total_facts}")
    print(f"  Distinct subjects: {len(subjects)}")
    print(f"  Tickets:           {len(generator.tickets)}")
    print(f"  Messages:          {len(generator.messages)}")
    print(f"  Planted conflicts: {len(generator.planted_conflicts)} (5 direct, 5 superseded, 4 undocumented)")
    print(f"Artifacts written to: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
