"""Constants and company structure for Northwind Logistics."""

from __future__ import annotations

TEAMS = [
    "Platform & Infrastructure",
    "Dispatch & Routing",
    "Warehouse Operations",
    "Cold Chain Logistics",
    "Carrier Billing & Finance",
    "Fleet Telematics & Safety",
    "Customs & Trade Compliance",
    "Customer Operations",
]

# 60 People across 8 teams
PEOPLE_RAW = [
    # Platform & Infrastructure (8)
    ("Tomas Okafor", "Principal Infrastructure Engineer", "Platform & Infrastructure", True),
    ("Elena Rostova", "Staff Site Reliability Engineer", "Platform & Infrastructure", True),
    ("Marcus Chen", "Senior Platform Engineer", "Platform & Infrastructure", True),
    ("Aisha Al-Mansoor", "Cloud Security Architect", "Platform & Infrastructure", True),
    ("Lukas Lindqvist", "DevOps Engineer", "Platform & Infrastructure", True),
    ("Chloe Martin", "Database Reliability Engineer", "Platform & Infrastructure", True),
    ("Kwame Mensah", "Infrastructure Engineer", "Platform & Infrastructure", True),
    ("Sarah Jenkins", "Systems Engineer", "Platform & Infrastructure", False),  # inactive
    # Dispatch & Routing (8)
    ("Sofia Alvarez", "Staff Optimization Engineer", "Dispatch & Routing", True),
    ("Arjun Patel", "Senior Routing Algorithms Engineer", "Dispatch & Routing", True),
    ("Hannah Schmidt", "Senior Dispatch Platform Engineer", "Dispatch & Routing", True),
    ("David Kim", "Backend Engineer", "Dispatch & Routing", True),
    ("Lucia Rossi", "Dispatch Operations Specialist", "Dispatch & Routing", True),
    ("Tariq Mahmoud", "Routing Data Analyst", "Dispatch & Routing", True),
    ("Nadia Benali", "Software Engineer", "Dispatch & Routing", True),
    ("Mateo Fernandez", "Associate Engineer", "Dispatch & Routing", True),
    # Warehouse Operations (7)
    ("Mei Lin Hart", "Director of Warehouse Automation", "Warehouse Operations", True),
    ("Viktor Novak", "Senior WMS Architect", "Warehouse Operations", True),
    ("Amara Okafor", "Warehouse Systems Specialist", "Warehouse Operations", True),
    ("Carlos Mendoza", "Lead Automation Engineer", "Warehouse Operations", True),
    ("Ingrid Hansen", "Inventory Control Specialist", "Warehouse Operations", True),
    ("Samuel Osei", "WMS Integration Engineer", "Warehouse Operations", True),
    ("Fatima Zahra", "Barcode & RFID Specialist", "Warehouse Operations", True),
    # Cold Chain Logistics (7)
    ("Priya Raman", "Cold Chain Platform Lead", "Cold Chain Logistics", True),
    ("Julian Moreau", "Reefer IoT Specialist", "Cold Chain Logistics", True),
    ("Astrid Nygard", "Quality Assurance Lead (Pharma)", "Cold Chain Logistics", True),
    ("Kenji Sato", "Senior Embedded Systems Engineer", "Cold Chain Logistics", True),
    ("Zainab Diallo", "Food Safety Compliance Officer", "Cold Chain Logistics", True),
    ("Dmitri Volkov", "Hardware Reliability Engineer", "Cold Chain Logistics", True),
    ("Beatrice Fontaine", "Cold Chain Operations Lead", "Cold Chain Logistics", False),  # inactive
    # Carrier Billing & Finance (8)
    ("Daniel Brandt", "Head of Financial Engineering", "Carrier Billing & Finance", True),
    ("Grace Mensah", "Carrier Billing Product Lead", "Carrier Billing & Finance", True),
    ("Arthur Pendelton", "Senior Settlement Architect", "Carrier Billing & Finance", True),
    ("Leila Farhat", "Financial Systems Analyst", "Carrier Billing & Finance", True),
    ("Pavel Horvath", "Payments Integration Engineer", "Carrier Billing & Finance", True),
    ("Sunita Rao", "Internal Controls Auditor", "Carrier Billing & Finance", True),
    ("Simon Becker", "Staff Ledger Engineer", "Carrier Billing & Finance", True),
    ("Ananya Sharma", "Disputes Resolution Analyst", "Carrier Billing & Finance", True),
    # Fleet Telematics & Safety (8)
    ("Jonas Weber", "Fleet Telematics Lead", "Fleet Telematics & Safety", True),
    ("Rachel Greenbaum", "Transportation Safety Officer", "Fleet Telematics & Safety", True),
    ("Felipe Santos", "Senior Telematics Firmware Engineer", "Fleet Telematics & Safety", True),
    ("Marta Kowalska", "Driver App Lead", "Fleet Telematics & Safety", True),
    ("Oliver Quinn", "Mobile Systems Engineer", "Fleet Telematics & Safety", True),
    ("Yuki Tanaka", "Sensor Telemetry Engineer", "Fleet Telematics & Safety", True),
    ("Gabriel Silva", "Safety Compliance Analyst", "Fleet Telematics & Safety", True),
    ("Noah Williams", "Field Diagnostics Specialist", "Fleet Telematics & Safety", True),
    # Customs & Trade Compliance (7)
    ("Hamid Rezaei", "Chief Customs Broker & Architect", "Customs & Trade Compliance", True),
    ("Valerie Dupont", "Cross-Border Regulatory Lead", "Customs & Trade Compliance", True),
    ("Liam O'Connor", "Customs Gateway Engineer", "Customs & Trade Compliance", True),
    ("Chen Wei", "Trade Compliance Auditor", "Customs & Trade Compliance", True),
    ("Soraya Hadad", "Import Declaration Specialist", "Customs & Trade Compliance", True),
    ("Mikhail Petrov", "EDI Integration Developer", "Customs & Trade Compliance", True),
    ("Camila Duarte", "Customs Ops Analyst", "Customs & Trade Compliance", True),
    # Customer Operations (7)
    ("Maya Lin", "VP Customer Operations", "Customer Operations", True),
    ("Benjamin Scott", "Customer Experience Architect", "Customer Operations", True),
    ("Farah Mansour", "Claims & Exceptions Lead", "Customer Operations", True),
    ("Tobias Meyer", "Senior SLA Operations Manager", "Customer Operations", True),
    ("Chioma Eze", "Customer Support Specialist", "Customer Operations", True),
    ("Lucas Silva", "Customer Systems Integrator", "Customer Operations", True),
    ("Katarina Holm", "Operations Escalation Specialist", "Customer Operations", False),  # inactive
]

SYSTEMS_RAW = [
    # Tier 1 systems (most critical, tier=1 -> weight=3)
    ("sys-dispatch-router", "Dispatch Router", "dispatch-router", 1, "usr-0009"),      # Sofia Alvarez
    ("sys-warehouse-wms", "Warehouse WMS", "warehouse-wms", 1, "usr-0017"),              # Mei Lin Hart
    ("sys-cold-chain-monitor", "Cold Chain Monitor", "cold-chain-monitor", 1, "usr-0024"),# Priya Raman
    ("sys-finance-ledger", "Finance Ledger", "finance-ledger", 1, "usr-0031"),          # Daniel Brandt
    ("sys-payments-gateway", "Payments Gateway", "payments-gateway", 1, "usr-0035"),    # Pavel Horvath

    # Tier 2 systems (tier=2 -> weight=2)
    ("sys-driver-app", "Driver App", "driver-app", 2, "usr-0042"),                      # Marta Kowalska
    ("sys-carrier-billing", "Carrier Billing", "carrier-billing", 2, "usr-0032"),        # Grace Mensah
    ("sys-customs-gateway", "Customs Gateway", "customs-gateway", 2, "usr-0047"),        # Hamid Rezaei
    ("sys-inventory-service", "Inventory Service", "inventory-service", 2, "usr-0018"),  # Viktor Novak
    ("sys-tracking-api", "Tracking API", "tracking-api", 2, "usr-0010"),                # Arjun Patel

    # Tier 3 systems (tier=3 -> weight=1)
    ("sys-fleet-telematics", "Fleet Telematics", "fleet-telematics", 3, "usr-0039"),    # Jonas Weber
    ("sys-notification-engine", "Notification Engine", "notification-engine", 3, "usr-0003"), # Marcus Chen
    ("sys-depot-kiosk", "Depot Kiosk", "depot-kiosk", 3, "usr-0020"),                   # Carlos Mendoza
    ("sys-analytics-pipeline", "Analytics Pipeline", "analytics-pipeline", 3, "usr-0014"), # Tariq Mahmoud
]

from data.models import SubjectEntity

# Aliases for entity resolution testing and corpus subject definitions
NORTHWIND_SUBJECTS: list[SubjectEntity] = [
    # ── 1. The 14 Planted Conflict Subjects (High priority / heavily documented) ──
    SubjectEntity(
        slug="carrier-invoice-dispute-window",
        name="Carrier Invoice Dispute Window",
        type="policy",
        aliases=["Carrier Invoice Dispute Window", "freight invoice dispute period", "carrier billing dispute timeline"],
    ),
    SubjectEntity(
        slug="a-class-cycle-count",
        name="A-Class SKU Cycle Count",
        type="process",
        aliases=["A-Class SKU Cycle Count", "A-class inventory cycle count", "tier A inventory count frequency"],
    ),
    SubjectEntity(
        slug="proof-of-delivery",
        name="Proof of Delivery",
        type="artifact",
        aliases=["Proof of Delivery", "electronic proof of delivery", "POD customer signature record", "delivery sign-off receipt"],
    ),
    SubjectEntity(
        slug="oncall-tier1-ack",
        name="Tier 1 On-Call Ack Target",
        type="policy",
        aliases=["Tier 1 On-Call Ack Target", "tier 1 incident acknowledgement target", "tier 1 platform pager SLA"],
    ),
    SubjectEntity(
        slug="damage-claim-auto-approval",
        name="Damage Claim Auto-Approval Threshold",
        type="policy",
        aliases=["Damage Claim Auto-Approval Threshold", "cargo damage self-service limit", "damage claim exception threshold"],
    ),
    SubjectEntity(
        slug="reefer-excursion-limit",
        name="Reefer Excursion Tolerance Duration",
        type="metric",
        aliases=["Reefer Excursion Tolerance Duration", "cold chain temperature excursion limit", "reefer probe duration threshold"],
    ),
    SubjectEntity(
        slug="driver-hours-limit",
        name="Driver Shift Hours Ceiling",
        type="policy",
        aliases=["Driver Shift Hours Ceiling", "maximum shift driving limit", "hours of service driving restriction"],
    ),
    SubjectEntity(
        slug="dispatch-router-retry-limit",
        name="Dispatch Solver Retry Ceiling",
        type="policy",
        aliases=["Dispatch Solver Retry Ceiling", "routing engine solver retry limit", "dispatch router external retry attempts"],
    ),
    SubjectEntity(
        slug="dock-late-cancellation-window",
        name="Dock Arrival Grace Period",
        type="process",
        aliases=["Dock Arrival Grace Period", "dock appointment late arrival window", "cross-dock check-in tolerance"],
    ),
    SubjectEntity(
        slug="gps-moving-ping-interval",
        name="GPS Telematics Moving Ping Interval",
        type="metric",
        aliases=["GPS Telematics Moving Ping Interval", "in-transit GPS reporting cadence", "fleet telemetry ping interval"],
    ),
    SubjectEntity(
        slug="dispatch-router",
        name="Dispatch Router",
        type="system",
        aliases=["Dispatch Router", "the routing engine", "dispatch-router", "the dispatch router service"],
    ),
    SubjectEntity(
        slug="customs-gateway",
        name="Customs Gateway",
        type="system",
        aliases=["Customs Gateway", "the cross-border declaration service", "customs-portal", "customs-gateway"],
    ),
    SubjectEntity(
        slug="payments-gateway",
        name="Payments Gateway",
        type="system",
        aliases=["Payments Gateway", "the payment processing service", "payments-gateway", "settlement-engine"],
    ),
    SubjectEntity(
        slug="cold-chain-monitor",
        name="Cold Chain Monitor",
        type="system",
        aliases=["Cold Chain Monitor", "the cold chain monitoring service", "reefer-monitor", "cold-chain-monitor"],
    ),

    # ── 2. Remaining Core Systems (system) ──
    SubjectEntity(
        slug="warehouse-wms",
        name="Warehouse WMS",
        type="system",
        aliases=["Warehouse WMS", "the warehouse management system", "WMS Core", "warehouse-wms"],
    ),
    SubjectEntity(
        slug="finance-ledger",
        name="Finance Ledger",
        type="system",
        aliases=["Finance Ledger", "the ledger service", "general-ledger", "finance-ledger"],
    ),
    SubjectEntity(
        slug="driver-app",
        name="Driver App",
        type="system",
        aliases=["Driver App", "the mobile driver client", "driver-app", "the driver mobile terminal"],
    ),
    SubjectEntity(
        slug="carrier-billing",
        name="Carrier Billing",
        type="system",
        aliases=["Carrier Billing", "the billing service", "carrier-billing", "the freight audit system"],
    ),
    SubjectEntity(
        slug="inventory-service",
        name="Inventory Service",
        type="system",
        aliases=["Inventory Service", "the inventory record service", "inventory-service", "stock-service"],
    ),
    SubjectEntity(
        slug="tracking-api",
        name="Tracking API",
        type="system",
        aliases=["Tracking API", "the shipment tracking service", "tracking-api", "public-tracking-service"],
    ),
    SubjectEntity(
        slug="fleet-telematics",
        name="Fleet Telematics",
        type="system",
        aliases=["Fleet Telematics", "the onboard vehicle telematics", "telematics-ingest", "fleet-telematics"],
    ),
    SubjectEntity(
        slug="notification-engine",
        name="Notification Engine",
        type="system",
        aliases=["Notification Engine", "the dispatch notifier", "notification-engine", "alert-dispatcher"],
    ),
    SubjectEntity(
        slug="depot-kiosk",
        name="Depot Kiosk",
        type="system",
        aliases=["Depot Kiosk", "the check-in kiosk terminal", "depot-kiosk", "dock-kiosk"],
    ),
    SubjectEntity(
        slug="analytics-pipeline",
        name="Analytics Pipeline",
        type="system",
        aliases=["Analytics Pipeline", "the logistics data warehouse", "analytics-pipeline", "reporting-lake"],
    ),
    SubjectEntity(
        slug="edi-translator",
        name="EDI Translator",
        type="system",
        aliases=["EDI Translator", "the electronic data interchange translator", "edi-translator", "edi-parser"],
    ),
    SubjectEntity(
        slug="fuel-card-manager",
        name="Fuel Card Manager",
        type="system",
        aliases=["Fuel Card Manager", "fleet card authorization system", "fuel-card-manager", "fuel-service"],
    ),
    SubjectEntity(
        slug="dock-scheduler",
        name="Dock Scheduler",
        type="system",
        aliases=["Dock Scheduler", "appointment booking engine", "dock-scheduler", "inbound-scheduling-service"],
    ),
    SubjectEntity(
        slug="trailer-lock-controller",
        name="Trailer Lock Controller",
        type="system",
        aliases=["Trailer Lock Controller", "electronic cargo seal service", "trailer-lock-controller", "smart-seal-daemon"],
    ),

    # ── 3. Policies (policy) ──
    SubjectEntity(
        slug="hazardous-materials-protocol",
        name="Hazardous Materials Protocol",
        type="policy",
        aliases=["Hazardous Materials Protocol", "HAZMAT transportation standard", "dangerous goods compliance rule"],
    ),
    SubjectEntity(
        slug="cross-border-compliance-rule",
        name="Cross-Border Compliance Rule",
        type="policy",
        aliases=["Cross-Border Compliance Rule", "international transit protocol", "customs regulatory guideline"],
    ),
    SubjectEntity(
        slug="visitor-depot-security-policy",
        name="Visitor Depot Security Policy",
        type="policy",
        aliases=["Visitor Depot Security Policy", "warehouse facility access rule", "terminal security guideline"],
    ),
    SubjectEntity(
        slug="overtime-authorization-policy",
        name="Overtime Authorization Policy",
        type="policy",
        aliases=["Overtime Authorization Policy", "warehouse shift overtime rule", "labor exception policy"],
    ),
    SubjectEntity(
        slug="fuel-reimbursement-guideline",
        name="Fuel Reimbursement Guideline",
        type="policy",
        aliases=["Fuel Reimbursement Guideline", "driver fuel expense policy", "off-network fuel rule"],
    ),
    SubjectEntity(
        slug="cargo-seal-integrity-standard",
        name="Cargo Seal Integrity Standard",
        type="policy",
        aliases=["Cargo Seal Integrity Standard", "trailer door seal protocol", "cargo seal inspection standard"],
    ),
    SubjectEntity(
        slug="pallet-exchange-agreement",
        name="Pallet Exchange Agreement",
        type="policy",
        aliases=["Pallet Exchange Agreement", "CHEP pallet return policy", "pallet liability terms"],
    ),
    SubjectEntity(
        slug="remote-access-security-policy",
        name="Remote Access Security Policy",
        type="policy",
        aliases=["Remote Access Security Policy", "engineering VPN access policy", "zero-trust infrastructure standard"],
    ),
    SubjectEntity(
        slug="driver-rest-break-rule",
        name="Driver Rest Break Rule",
        type="policy",
        aliases=["Driver Rest Break Rule", "mandatory driver rest period", "rest interval standard"],
    ),
    SubjectEntity(
        slug="reefer-pre-cooling-standard",
        name="Reefer Pre-Cooling Standard",
        type="policy",
        aliases=["Reefer Pre-Cooling Standard", "trailer chill-down requirement", "pre-trip refrigeration rule"],
    ),

    # ── 4. Metrics (metric) ──
    SubjectEntity(
        slug="on-time-dispatch-rate",
        name="On-Time Dispatch Rate",
        type="metric",
        aliases=["On-Time Dispatch Rate", "dispatch punctuality percentage", "departure timeliness score"],
    ),
    SubjectEntity(
        slug="dock-dwell-time",
        name="Dock Dwell Time",
        type="metric",
        aliases=["Dock Dwell Time", "average trailer dock dwell minutes", "unloading turnaround time"],
    ),
    SubjectEntity(
        slug="temperature-excursion-count",
        name="Temperature Excursion Count",
        type="metric",
        aliases=["Temperature Excursion Count", "monthly reefer temperature violations", "excursion frequency count"],
    ),
    SubjectEntity(
        slug="driver-turnaround-minutes",
        name="Driver Turnaround Minutes",
        type="metric",
        aliases=["Driver Turnaround Minutes", "depot gate-to-gate turnaround duration", "driver facility wait time"],
    ),
    SubjectEntity(
        slug="invoice-dispute-resolution-days",
        name="Invoice Dispute Resolution Days",
        type="metric",
        aliases=["Invoice Dispute Resolution Days", "freight audit dispute turnaround", "carrier dispute resolution days"],
    ),
    SubjectEntity(
        slug="lane-deadhead-percentage",
        name="Lane Deadhead Percentage",
        type="metric",
        aliases=["Lane Deadhead Percentage", "empty repositioning mile ratio", "lane deadhead percentage"],
    ),
    SubjectEntity(
        slug="inventory-shrinkage-rate",
        name="Inventory Shrinkage Rate",
        type="metric",
        aliases=["Inventory Shrinkage Rate", "warehouse stock variance percentage", "annual inventory shrinkage rate"],
    ),
    SubjectEntity(
        slug="fleet-fuel-economy-mpg",
        name="Fleet Fuel Economy MPG",
        type="metric",
        aliases=["Fleet Fuel Economy MPG", "fleet tractor fuel efficiency", "average miles per gallon"],
    ),
    SubjectEntity(
        slug="edi-parse-error-rate",
        name="EDI Parse Error Rate",
        type="metric",
        aliases=["EDI Parse Error Rate", "edi document syntax failure rate", "edi transaction rejection rate"],
    ),
    SubjectEntity(
        slug="trailer-utilization-ratio",
        name="Trailer Utilization Ratio",
        type="metric",
        aliases=["Trailer Utilization Ratio", "cubic capacity utilization factor", "fleet trailer fill rate"],
    ),
    SubjectEntity(
        slug="first-pass-count-accuracy",
        name="First-Pass Count Accuracy",
        type="metric",
        aliases=["First-Pass Count Accuracy", "initial cycle count match percentage", "cycle count precision rate"],
    ),

    # ── 5. Processes (process) ──
    SubjectEntity(
        slug="month-end-financial-close",
        name="Month-End Financial Close",
        type="process",
        aliases=["Month-End Financial Close", "finance ledger closing procedure", "month-end accounting close"],
    ),
    SubjectEntity(
        slug="morning-wave-release",
        name="Morning Wave Release",
        type="process",
        aliases=["Morning Wave Release", "warehouse order wave release workflow", "morning pick batch dispatch"],
    ),
    SubjectEntity(
        slug="dock-appointment-booking",
        name="Dock Appointment Booking",
        type="process",
        aliases=["Dock Appointment Booking", "carrier dock reservation process", "inbound dock booking workflow"],
    ),
    SubjectEntity(
        slug="reefer-breakdown-triage",
        name="Reefer Breakdown Triage",
        type="process",
        aliases=["Reefer Breakdown Triage", "in-transit refrigeration repair protocol", "reefer unit failure triage"],
    ),
    SubjectEntity(
        slug="carrier-onboarding-workflow",
        name="Carrier Onboarding Workflow",
        type="process",
        aliases=["Carrier Onboarding Workflow", "freight carrier vetting process", "new carrier compliance verification"],
    ),
    SubjectEntity(
        slug="driver-shift-handover",
        name="Driver Shift Handover",
        type="process",
        aliases=["Driver Shift Handover", "slip-seat tractor exchange procedure", "driver cab transfer checklist"],
    ),
    SubjectEntity(
        slug="returns-pallet-inspection",
        name="Returns Pallet Inspection",
        type="process",
        aliases=["Returns Pallet Inspection", "damaged goods quarantine inspection", "returns staging process"],
    ),
    SubjectEntity(
        slug="trailer-decontamination-wash",
        name="Trailer Decontamination Wash",
        type="process",
        aliases=["Trailer Decontamination Wash", "food-grade trailer sanitization", "reefer washout procedure"],
    ),
    SubjectEntity(
        slug="customs-brokerage-escalation",
        name="Customs Brokerage Escalation",
        type="process",
        aliases=["Customs Brokerage Escalation", "border hold resolution protocol", "customs delay triage"],
    ),
    SubjectEntity(
        slug="lane-capacity-auction",
        name="Lane Capacity Auction",
        type="process",
        aliases=["Lane Capacity Auction", "spot market lane bidding process", "freight broker capacity auction"],
    ),
    SubjectEntity(
        slug="lost-in-transit-investigation",
        name="Lost in Transit Investigation",
        type="process",
        aliases=["Lost in Transit Investigation", "missing pallet search protocol", "cargo loss escalation"],
    ),

    # ── 6. Artifacts (artifact) ──
    SubjectEntity(
        slug="bill-of-lading",
        name="Bill of Lading",
        type="artifact",
        aliases=["Bill of Lading", "standard freight bill of lading", "shipping manifest paper"],
    ),
    SubjectEntity(
        slug="rate-confirmation-sheet",
        name="Rate Confirmation Sheet",
        type="artifact",
        aliases=["Rate Confirmation Sheet", "carrier agreed rate confirmation", "freight rate tender document"],
    ),
    SubjectEntity(
        slug="cold-chain-data-log",
        name="Cold Chain Data Log",
        type="artifact",
        aliases=["Cold Chain Data Log", "reefer probe temperature datalog", "temperature audit record"],
    ),
    SubjectEntity(
        slug="commercial-customs-invoice",
        name="Commercial Customs Invoice",
        type="artifact",
        aliases=["Commercial Customs Invoice", "cross-border commercial invoice", "customs valuation document"],
    ),
    SubjectEntity(
        slug="cycle-count-variance-report",
        name="Cycle Count Variance Report",
        type="artifact",
        aliases=["Cycle Count Variance Report", "WMS stock discrepancy sheet", "warehouse inventory audit summary"],
    ),
    SubjectEntity(
        slug="driver-inspection-log",
        name="Driver Inspection Log",
        type="artifact",
        aliases=["Driver Inspection Log", "daily vehicle pre-trip log", "DVIR safety inspection record"],
    ),
    SubjectEntity(
        slug="pallet-manifest-barcode",
        name="Pallet Manifest Barcode",
        type="artifact",
        aliases=["Pallet Manifest Barcode", "license plate barcode label", "LPN pallet tracking tag"],
    ),
    SubjectEntity(
        slug="electronic-customs-declaration",
        name="Electronic Customs Declaration",
        type="artifact",
        aliases=["Electronic Customs Declaration", "advance cargo EDI declaration", "customs entry summary"],
    ),
    SubjectEntity(
        slug="carrier-contract-addendum",
        name="Carrier Contract Addendum",
        type="artifact",
        aliases=["Carrier Contract Addendum", "fuel surcharge contract schedule", "broker-carrier agreement rider"],
    ),
    SubjectEntity(
        slug="trailer-inspection-certificate",
        name="Trailer Inspection Certificate",
        type="artifact",
        aliases=["Trailer Inspection Certificate", "annual DOT vehicle inspection document", "trailer roadworthiness certificate"],
    ),
]

SUBJECT_MAP: dict[str, SubjectEntity] = {s.slug: s for s in NORTHWIND_SUBJECTS}
SUBJECT_ALIASES: dict[str, list[str]] = {s.slug: s.aliases for s in NORTHWIND_SUBJECTS}

CHANNELS = [
    "#infra",
    "#payments",
    "#oncall",
    "#dispatch-oncall",
    "#warehouse-ops",
    "#cold-chain-ops",
    "#fleet-safety",
    "#customs-brokerage",
    "#customer-escalations",
    "#architecture-decisions",
]

