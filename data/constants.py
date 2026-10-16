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

# Aliases for entity resolution testing
SUBJECT_ALIASES: dict[str, list[str]] = {
    "dispatch-router": ["Dispatch Router", "the routing engine", "dispatch-router", "the dispatch router service"],
    "warehouse-wms": ["Warehouse WMS", "the warehouse management system", "WMS Core", "warehouse-wms"],
    "cold-chain-monitor": ["Cold Chain Monitor", "the cold chain monitoring service", "reefer-monitor", "cold-chain-monitor"],
    "finance-ledger": ["Finance Ledger", "the ledger service", "general-ledger", "finance-ledger"],
    "payments-gateway": ["Payments Gateway", "the payment processing service", "payments-gateway", "payment-service"],
    "driver-app": ["Driver App", "the mobile driver client", "driver-app", "the driver mobile terminal"],
    "carrier-billing": ["Carrier Billing", "the billing service", "carrier-billing", "the freight audit system"],
    "customs-gateway": ["Customs Gateway", "the cross-border declaration service", "customs-gateway", "customs-portal"],
    "inventory-service": ["Inventory Service", "the inventory record service", "inventory-service", "stock-service"],
    "tracking-api": ["Tracking API", "the shipment tracking service", "tracking-api", "public-tracking-service"],
    "fleet-telematics": ["Fleet Telematics", "the onboard vehicle telematics", "telematics-ingest", "fleet-telematics"],
    "notification-engine": ["Notification Engine", "the dispatch notifier", "notification-engine", "alert-dispatcher"],
    "depot-kiosk": ["Depot Kiosk", "the check-in kiosk terminal", "depot-kiosk", "dock-kiosk"],
    "analytics-pipeline": ["Analytics Pipeline", "the logistics data warehouse", "analytics-pipeline", "reporting-lake"],
}

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
