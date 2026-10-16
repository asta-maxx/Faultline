"""Architectural Decision Records (ADRs) and SUPERSEDES chains for Northwind Logistics."""

from __future__ import annotations

from data.models import DecisionData

# Definition of 14 chains totaling 40 ADRs with depths 2 to 4.
# Each tuple: (chain_topic, [(ref_num, title, author_id, base_year, summary, accepted_value)])
RAW_ADR_CHAINS = [
    # Chain 1 (Depth 3): Reefer Excursion Tolerance (Democase Plant 6)
    (
        "reefer-excursion-tolerance",
        [
            (41, "ADR-41: Reefer excursion tolerance limit", "usr-0024", 2023, 1,
             "Tolerate reefer excursions above 8 degrees C for up to 30 minutes before rejecting load.", "30 minutes"),
            (63, "ADR-63: Tighter excursion tolerance for pharma", "usr-0026", 2024, 6,
             "Pharmaceutical reefer loads rejected after 20 minutes above 8 degrees C; general cargo stays 30 minutes.", "20 minutes"),
            (88, "ADR-88: Single excursion limit for all reefer loads", "usr-0024", 2025, 3,
             "Every reefer load is rejected after 15 minutes above 8 degrees C regardless of cargo type.", "15 minutes"),
        ]
    ),
    # Chain 2 (Depth 2): Driver Hours Limit (Democase Plant 7)
    (
        "driver-hours-limit",
        [
            (30, "ADR-30: Maximum consecutive driving hours per shift", "usr-0040", 2023, 4,
             "Drivers blocked from accepting new loads after 11 hours of driving in a shift.", "11 hours"),
            (74, "ADR-74: Stricter shift driving time limits for driver safety", "usr-0040", 2025, 1,
             "No driver may drive more than 10 hours in a shift across all lanes.", "10 hours"),
        ]
    ),
    # Chain 3 (Depth 3): Dispatch Router Retry Limit (Democase Plant 8)
    (
        "dispatch-router-retry-limit",
        [
            (18, "ADR-18: Routing engine external solver retry attempts", "usr-0009", 2023, 2,
             "External solver calls are retried up to 3 times before fallback.", "3 attempts"),
            (35, "ADR-35: Intermediate retry backoff adjustment", "usr-0010", 2024, 2,
             "Solver calls retried 2 times with exponential backoff.", "2 attempts"),
            (52, "ADR-52: Single retry ceiling for dispatch solver calls", "usr-0009", 2025, 4,
             "External solver calls retried exactly 1 time to prevent cascade timeouts.", "1 attempt"),
        ]
    ),
    # Chain 4 (Depth 2): Dock Scheduling Late Window (Democase Plant 9)
    (
        "dock-late-cancellation-window",
        [
            (22, "ADR-22: Warehouse dock arrival grace period", "usr-0017", 2023, 5,
             "Carriers arriving within 60 minutes of scheduled slot retain dock priority.", "60 minutes"),
            (68, "ADR-68: Tightened dock arrival window for cross-dock facilities", "usr-0017", 2025, 2,
             "Carriers arriving more than 30 minutes late lose dock appointment and are rescheduled.", "30 minutes"),
        ]
    ),
    # Chain 5 (Depth 2): Fleet Telematics Ping Interval (Democase Plant 10)
    (
        "gps-moving-ping-interval",
        [
            (12, "ADR-12: High-density GPS reporting for long-haul tractors", "usr-0039", 2023, 3,
             "Tractors transmit GPS telematics ping every 15 seconds while moving.", "15 seconds"),
            (49, "ADR-49: Normalized telemetry transmission interval", "usr-0039", 2024, 11,
             "Tractors transmit GPS telematics ping every 30 seconds while moving to conserve cellular bandwidth.", "30 seconds"),
        ]
    ),
    # Chain 6 (Depth 3): Carrier Invoice Payment Terms
    (
        "carrier-invoice-payment-terms",
        [
            (15, "ADR-15: Standard carrier payment terms", "usr-0032", 2023, 3,
             "Standard carrier settlements processed on Net 60 terms.", "Net 60"),
            (44, "ADR-44: Quick-pay discount settlement schedule", "usr-0032", 2024, 5,
             "Preferred carriers settled on Net 45 terms with 1 percent discount.", "Net 45"),
            (71, "ADR-71: Unified freight settlement schedule", "usr-0031", 2025, 5,
             "All approved carrier freight settlements execute on Net 30 terms.", "Net 30"),
        ]
    ),
    # Chain 7 (Depth 4): Payments Settlement Idempotency Window
    (
        "payments-idempotency-window",
        [
            (8, "ADR-08: Basic payment transaction deduplication", "usr-0035", 2022, 10,
             "Idempotency cache stores payment transaction tokens for 6 hours.", "6 hours"),
            (27, "ADR-27: Extended payment token caching", "usr-0035", 2023, 8,
             "Payment idempotency keys retained for 12 hours in distributed cache.", "12 hours"),
            (56, "ADR-56: 24-hour settlement idempotency window", "usr-0031", 2024, 9,
             "Payments Gateway caches settlement idempotency keys for 24 hours.", "24 hours"),
            (82, "ADR-82: Multi-day idempotency key retention", "usr-0035", 2025, 7,
             "Payments Gateway retains transaction idempotency keys for 48 hours.", "48 hours"),
        ]
    ),
    # Chain 8 (Depth 3): Customs Filing Lead Time
    (
        "customs-filing-lead-time",
        [
            (14, "ADR-14: Cross-border pre-arrival declaration timing", "usr-0047", 2023, 4,
             "Customs declarations filed 12 hours prior to port arrival.", "12 hours"),
            (38, "ADR-38: Standardized pre-clearance window", "usr-0047", 2024, 3,
             "Cross-border declarations submitted 24 hours prior to border crossing.", "24 hours"),
            (79, "ADR-79: Advance manifest electronic submission protocol", "usr-0048", 2025, 6,
             "Electronic import declarations filed exactly 48 hours before scheduled arrival.", "48 hours"),
        ]
    ),
    # Chain 9 (Depth 3): Warehouse Cycle Count Frequency
    (
        "cycle-count-frequency",
        [
            (19, "ADR-19: Initial perpetual inventory cycle count policy", "usr-0018", 2023, 6,
             "A-class inventory cycle counts conducted once per month.", "monthly"),
            (46, "ADR-46: Bi-weekly counting schedule for high-velocity SKUs", "usr-0017", 2024, 7,
             "A-class inventory cycle counts conducted bi-weekly on alternating Tuesdays.", "bi-weekly"),
            (77, "ADR-77: Weekly cycle counting mandate for tier-1 distribution centers", "usr-0017", 2025, 4,
             "A-class items cycle counted every week across all distribution facilities.", "weekly"),
        ]
    ),
    # Chain 10 (Depth 3): Cold Chain Secondary Logger Retention
    (
        "secondary-logger-retention",
        [
            (21, "ADR-21: Reefer temperature logging record retention", "usr-0027", 2023, 7,
             "Secondary trailer temperature log data preserved for 90 days.", "90 days"),
            (50, "ADR-50: Compliance retention extension for cold storage logs", "usr-0028", 2024, 8,
             "Trailer temperature logging records preserved for 180 days.", "180 days"),
            (85, "ADR-85: 400-day audit retention mandate for reefer telemetry", "usr-0024", 2025, 8,
             "Secondary cold chain temperature logs retained for 400 days.", "400 days"),
        ]
    ),
    # Chain 11 (Depth 3): Proof of Delivery Document Upload Window
    (
        "proof-of-delivery-upload-window",
        [
            (16, "ADR-16: Mobile proof of delivery transmission schedule", "usr-0042", 2023, 5,
             "Drivers must transmit delivery receipts within 48 hours of drop-off.", "48 hours"),
            (43, "ADR-43: Same-day POD transmission requirement", "usr-0040", 2024, 4,
             "Proof of delivery photos must be uploaded within 24 hours of delivery.", "24 hours"),
            (73, "ADR-73: Real-time electronic delivery confirmation protocol", "usr-0042", 2025, 3,
             "Signed delivery confirmations must be synced to server within 4 hours.", "4 hours"),
        ]
    ),
    # Chain 12 (Depth 3): Dispatch Assignment Push Timeout
    (
        "dispatch-assignment-push-timeout",
        [
            (25, "ADR-25: Driver assignment notification delivery timeout", "usr-0011", 2023, 9,
             "Dispatched load offers to driver mobile app expire after 120 seconds.", "120 seconds"),
            (58, "ADR-58: Accelerated load dispatch offer window", "usr-0009", 2024, 10,
             "Dispatched load offers to driver mobile app expire after 60 seconds.", "60 seconds"),
            (84, "ADR-84: High-throughput dispatch load offer duration", "usr-0009", 2025, 7,
             "Dispatched load offers to driver mobile app expire after 30 seconds.", "30 seconds"),
        ]
    ),
    # Chain 13 (Depth 3): Oncall Alert Escalation SLA
    (
        "oncall-tier1-escalation-sla",
        [
            (17, "ADR-17: Baseline tier 1 on-call pager acknowledgement window", "usr-0002", 2023, 3,
             "Tier 1 service pages must be acknowledged within 30 minutes.", "30 minutes"),
            (47, "ADR-47: Critical incident response time reduction", "usr-0001", 2024, 6,
             "Tier 1 service pages must be acknowledged within 15 minutes.", "15 minutes"),
            (81, "ADR-81: Ultra-critical platform incident response SLA", "usr-0002", 2025, 6,
             "Tier 1 critical alerts require primary on-call acknowledgement within 10 minutes.", "10 minutes"),
        ]
    ),
    # Chain 14 (Depth 3): Customer Damage Claim Auto-Approval Threshold
    (
        "damage-claim-auto-approval-limit",
        [
            (23, "ADR-23: Customer damage claim exception threshold", "usr-0056", 2023, 8,
             "Damage claims under 100 USD approved automatically without human review.", "100 USD"),
            (53, "ADR-53: Expanded self-service resolution dollar threshold", "usr-0055", 2024, 9,
             "Damage claims under 250 USD approved automatically without human review.", "250 USD"),
            (87, "ADR-87: Tiered automatic exception resolution threshold", "usr-0054", 2025, 8,
             "Damage claims under 400 USD approved automatically without human review.", "400 USD"),
        ]
    ),
]


def generate_decisions() -> list[DecisionData]:
    """Generates the 40 Decision nodes linked by SUPERSEDES chains (newer -> older)."""
    decisions: list[DecisionData] = []
    
    for _, chain in RAW_ADR_CHAINS:
        prev_dec_id: str | None = None
        for i, (ref_num, title, author_id, base_year, month, summary, val) in enumerate(chain):
            is_latest = (i == len(chain) - 1)
            status = "accepted" if is_latest else "superseded"
            dec_id = f"dec-{ref_num:04d}"
            # Construct deterministic timestamp
            # Epoch for year/month: e.g. 2023-01-15 -> ~1673740800
            # Approx: (year - 1970) * 31536000 + (month - 1) * 2592000 + 15 * 86400
            decided_at = (base_year - 1970) * 31536000 + (month - 1) * 2592000 + 15 * 86400
            
            # The supersedes pointer points newer -> older
            # When on step i (older), it has no supersedes_id yet.
            # When on step i > 0, this decision supersedes prev_dec_id!
            supersedes_id = prev_dec_id if i > 0 else None
            
            text = (
                f"Status: {status}.\n"
                f"{f'Supersedes ADR-{chain[i-1][0]:02d}.' if supersedes_id else ''}\n"
                f"Context: Northwind Logistics architecture standardization.\n"
                f"Decision: {summary} Accepted value is {val}.\n"
                f"Consequences: Downstream runbooks and service specifications must align."
            )
            
            dec = DecisionData(
                id=dec_id,
                ref=f"ADR-{ref_num}",
                title=title,
                status=status,
                decided_at=decided_at,
                author_id=author_id,
                supersedes_id=supersedes_id,
                text=text.strip()
            )
            decisions.append(dec)
            prev_dec_id = dec_id

    return decisions
