"""Loads Northwind Logistics structural graph into FalkorDB per CONTRACT §5.

Loads ONLY structural entities: Person, System, Decision, Document, Ticket, Message
and structural relationships: OWNS, AUTHORED, SUPERSEDES, GOVERNS, CITES.

NEVER creates: Claim, Entity, ASSERTS, ABOUT, CONTRADICTS, Conflict, INVOLVES, RESOLVED_AS.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any

from data.generate import NorthwindGenerator
from graph.connection import DEFAULT_TENANT, get_graph, graph_name
from graph.schema import apply_schema


def seed_structural_graph(
    tenant_id: str = DEFAULT_TENANT,
    reset: bool = False,
    merge: bool = False,
    generator_seed: int = 42,
    batch_size: int = 500,
) -> dict[str, Any]:
    """Applies schema and seeds structural nodes and relationships in batches via UNWIND.
    Verifies that loaded counts match generated counts and that runtime is < 30s.
    If merge=True, uses MERGE to preserve existing claims/entities and avoid duplicate documents.
    """
    if reset and merge:
        raise ValueError("Cannot specify both reset=True and merge=True.")

    start_time = time.perf_counter()
    g = get_graph(tenant_id)

    # 1. Reset graph if requested
    if reset:
        try:
            g.delete()
        except Exception:
            # Graph may not exist yet
            pass

    # 2. Idempotent schema initialization (constraints + indexes)
    schema_res = apply_schema(tenant_id=tenant_id)

    # 3. Generate deterministic structural entities
    gen = NorthwindGenerator(seed=generator_seed)
    gen.generate_all()

    # 4. Ingest Nodes in batches using UNWIND $rows
    # 4.1 Person
    person_rows = [
        {"id": p.id, "name": p.name, "role": p.role, "active": p.active}
        for p in gen.people
    ]
    person_cypher = (
        "UNWIND $rows AS row MERGE (p:Person {id: row.id}) SET p.name = row.name, p.role = row.role, p.active = row.active"
        if merge
        else "UNWIND $rows AS row CREATE (:Person {id: row.id, name: row.name, role: row.role, active: row.active})"
    )
    for i in range(0, len(person_rows), batch_size):
        g.query(person_cypher, {"rows": person_rows[i : i + batch_size]})

    # 4.2 System
    system_rows = [
        {"id": s.id, "name": s.name, "tier": s.tier}
        for s in gen.systems
    ]
    system_cypher = (
        "UNWIND $rows AS row MERGE (s:System {id: row.id}) SET s.name = row.name, s.tier = row.tier"
        if merge
        else "UNWIND $rows AS row CREATE (:System {id: row.id, name: row.name, tier: row.tier})"
    )
    for i in range(0, len(system_rows), batch_size):
        g.query(system_cypher, {"rows": system_rows[i : i + batch_size]})

    # 4.3 Decision
    decision_rows = [
        {
            "id": d.id,
            "ref": d.ref,
            "title": d.title,
            "status": d.status,
            "decided_at": d.decided_at,
        }
        for d in gen.decisions
    ]
    decision_cypher = (
        "UNWIND $rows AS row MERGE (d:Decision {id: row.id}) SET d.ref = row.ref, d.title = row.title, d.status = row.status, d.decided_at = row.decided_at"
        if merge
        else "UNWIND $rows AS row CREATE (:Decision {id: row.id, ref: row.ref, title: row.title, status: row.status, decided_at: row.decided_at})"
    )
    for i in range(0, len(decision_rows), batch_size):
        g.query(decision_cypher, {"rows": decision_rows[i : i + batch_size]})

    # 4.4 Document
    document_rows = [
        {
            "id": doc.id,
            "title": doc.title,
            "path": doc.path,
            "kind": doc.kind,
            "updated_at": doc.updated_at,
        }
        for doc in gen.documents
    ]
    doc_cypher = (
        "UNWIND $rows AS row MERGE (doc:Document {id: row.id}) SET doc.title = row.title, doc.path = row.path, doc.kind = row.kind, doc.updated_at = row.updated_at"
        if merge
        else "UNWIND $rows AS row CREATE (:Document {id: row.id, title: row.title, path: row.path, kind: row.kind, updated_at: row.updated_at})"
    )
    for i in range(0, len(document_rows), batch_size):
        g.query(doc_cypher, {"rows": document_rows[i : i + batch_size]})

    # 4.5 Ticket
    ticket_rows = [
        {
            "id": t.id,
            "ref": t.ref,
            "title": t.title,
            "text": t.text,
            "state": t.state,
            "closed_at": t.closed_at,
        }
        for t in gen.tickets
    ]
    ticket_cypher = (
        "UNWIND $rows AS row MERGE (t:Ticket {id: row.id}) SET t.ref = row.ref, t.title = row.title, t.text = row.text, t.state = row.state, t.closed_at = row.closed_at"
        if merge
        else "UNWIND $rows AS row CREATE (:Ticket {id: row.id, ref: row.ref, title: row.title, text: row.text, state: row.state, closed_at: row.closed_at})"
    )
    for i in range(0, len(ticket_rows), batch_size):
        g.query(ticket_cypher, {"rows": ticket_rows[i : i + batch_size]})

    # 4.6 Message
    message_rows = [
        {
            "id": m.id,
            "channel": m.channel,
            "text": m.text,
            "sent_at": m.sent_at,
        }
        for m in gen.messages
    ]
    msg_cypher = (
        "UNWIND $rows AS row MERGE (m:Message {id: row.id}) SET m.channel = row.channel, m.text = row.text, m.sent_at = row.sent_at"
        if merge
        else "UNWIND $rows AS row CREATE (:Message {id: row.id, channel: row.channel, text: row.text, sent_at: row.sent_at})"
    )
    for i in range(0, len(message_rows), batch_size):
        g.query(msg_cypher, {"rows": message_rows[i : i + batch_size]})

    # 5. Ingest Relationships in batches using UNWIND $rows
    # 5.1 OWNS: Person -> System
    rel_op = "MERGE" if merge else "CREATE"
    owns_rows = [{"from_id": s.owner_id, "to_id": s.id} for s in gen.systems]
    for i in range(0, len(owns_rows), batch_size):
        g.query(
            "UNWIND $rows AS row "
            "MATCH (p:Person {id: row.from_id}), (s:System {id: row.to_id}) "
            f"{rel_op} (p)-[:OWNS]->(s)",
            {"rows": owns_rows[i : i + batch_size]},
        )

    # 5.2 AUTHORED: Person -> Decision
    auth_dec_rows = [{"from_id": d.author_id, "to_id": d.id} for d in gen.decisions]
    for i in range(0, len(auth_dec_rows), batch_size):
        g.query(
            "UNWIND $rows AS row "
            "MATCH (p:Person {id: row.from_id}), (d:Decision {id: row.to_id}) "
            f"{rel_op} (p)-[:AUTHORED]->(d)",
            {"rows": auth_dec_rows[i : i + batch_size]},
        )

    # 5.3 SUPERSEDES: Decision -> Decision (newer -> older)
    supersedes_rows = [
        {"from_id": d.id, "to_id": d.supersedes_id}
        for d in gen.decisions
        if d.supersedes_id
    ]
    for i in range(0, len(supersedes_rows), batch_size):
        g.query(
            "UNWIND $rows AS row "
            "MATCH (newer:Decision {id: row.from_id}), (older:Decision {id: row.to_id}) "
            f"{rel_op} (newer)-[:SUPERSEDES]->(older)",
            {"rows": supersedes_rows[i : i + batch_size]},
        )

    # 5.4 AUTHORED: Person -> Document
    auth_doc_rows = [{"from_id": doc.author_id, "to_id": doc.id} for doc in gen.documents]
    for i in range(0, len(auth_doc_rows), batch_size):
        g.query(
            "UNWIND $rows AS row "
            "MATCH (p:Person {id: row.from_id}), (d:Document {id: row.to_id}) "
            f"{rel_op} (p)-[:AUTHORED]->(d)",
            {"rows": auth_doc_rows[i : i + batch_size]},
        )

    # 5.5 GOVERNS: Document -> System
    governs_rows = [
        {"from_id": doc.id, "to_id": sys_id}
        for doc in gen.documents
        for sys_id in doc.governs_system_ids
    ]
    for i in range(0, len(governs_rows), batch_size):
        g.query(
            "UNWIND $rows AS row "
            "MATCH (d:Document {id: row.from_id}), (s:System {id: row.to_id}) "
            f"{rel_op} (d)-[:GOVERNS]->(s)",
            {"rows": governs_rows[i : i + batch_size]},
        )

    # 5.6 CITES: Document -> Decision
    cites_rows = [
        {"from_id": doc.id, "to_id": dec_id}
        for doc in gen.documents
        for dec_id in doc.cites_decision_ids
    ]
    for i in range(0, len(cites_rows), batch_size):
        g.query(
            "UNWIND $rows AS row "
            "MATCH (d:Document {id: row.from_id}), (dec:Decision {id: row.to_id}) "
            f"{rel_op} (d)-[:CITES]->(dec)",
            {"rows": cites_rows[i : i + batch_size]},
        )

    elapsed = time.perf_counter() - start_time

    # 6. Verify counts against generator
    node_counts = {
        "Person": g.ro_query("MATCH (n:Person) RETURN count(n)").result_set[0][0],
        "System": g.ro_query("MATCH (n:System) RETURN count(n)").result_set[0][0],
        "Decision": g.ro_query("MATCH (n:Decision) RETURN count(n)").result_set[0][0],
        "Document": g.ro_query("MATCH (n:Document) RETURN count(n)").result_set[0][0],
        "Ticket": g.ro_query("MATCH (n:Ticket) RETURN count(n)").result_set[0][0],
        "Message": g.ro_query("MATCH (n:Message) RETURN count(n)").result_set[0][0],
    }

    edge_counts = {
        "OWNS": g.ro_query("MATCH ()-[r:OWNS]->() RETURN count(r)").result_set[0][0],
        "AUTHORED": g.ro_query("MATCH ()-[r:AUTHORED]->() RETURN count(r)").result_set[0][0],
        "SUPERSEDES": g.ro_query("MATCH ()-[r:SUPERSEDES]->() RETURN count(r)").result_set[0][0],
        "GOVERNS": g.ro_query("MATCH ()-[r:GOVERNS]->() RETURN count(r)").result_set[0][0],
        "CITES": g.ro_query("MATCH ()-[r:CITES]->() RETURN count(r)").result_set[0][0],
    }

    if not merge:
        # Prohibited labels and edge types check
        prohibited_labels = ("Claim", "Entity", "Conflict")
        prohibited_edges = ("ASSERTS", "ABOUT", "CONTRADICTS", "INVOLVES", "RESOLVED_AS")

        for lbl in prohibited_labels:
            cnt = g.ro_query(f"MATCH (n:{lbl}) RETURN count(n)").result_set[0][0]
            if cnt != 0:
                raise AssertionError(f"Prohibited label {lbl} found with count {cnt} in structural seed!")

        for rel in prohibited_edges:
            cnt = g.ro_query(f"MATCH ()-[r:{rel}]->() RETURN count(r)").result_set[0][0]
            if cnt != 0:
                raise AssertionError(f"Prohibited edge {rel} found with count {cnt} in structural seed!")
    else:
        # In merge mode, verify no duplicate documents, tickets, or messages exist
        for lbl in ("Document", "Ticket", "Message"):
            dups = g.ro_query(
                f"MATCH (n:{lbl}) WITH n.id AS nid, count(*) AS c WHERE c > 1 RETURN nid"
            ).result_set
            if dups:
                raise AssertionError(f"Duplicate {lbl} IDs found after merge seed: {dups}")

    expected_nodes = {
        "Person": len(gen.people),
        "System": len(gen.systems),
        "Decision": len(gen.decisions),
        "Document": len(gen.documents),
        "Ticket": len(gen.tickets),
        "Message": len(gen.messages),
    }

    expected_edges = {
        "OWNS": len(gen.systems),
        "AUTHORED": len(gen.decisions) + len(gen.documents),
        "SUPERSEDES": sum(1 for d in gen.decisions if d.supersedes_id),
        "GOVERNS": sum(len(d.governs_system_ids) for d in gen.documents),
        "CITES": sum(len(d.cites_decision_ids) for d in gen.documents),
    }

    for lbl, count in expected_nodes.items():
        if node_counts[lbl] != count:
            raise AssertionError(f"Node count mismatch for {lbl}: got {node_counts[lbl]}, expected {count}")

    for edge, count in expected_edges.items():
        if edge_counts[edge] != count:
            raise AssertionError(f"Edge count mismatch for {edge}: got {edge_counts[edge]}, expected {count}")

    if elapsed > 30.0:
        raise TimeoutError(f"Seeding took {elapsed:.2f} s, which exceeds 30 s threshold")

    return {
        "tenant_id": tenant_id,
        "graph": graph_name(tenant_id),
        "elapsed_seconds": elapsed,
        "node_counts": node_counts,
        "edge_counts": edge_counts,
        "schema": schema_res,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Northwind Logistics structural graph into FalkorDB.")
    parser.add_argument("--tenant", type=str, default=DEFAULT_TENANT, help="Tenant ID (default: northwind)")
    parser.add_argument("--reset", action="store_true", help="Delete and recreate graph before seeding")
    parser.add_argument("--merge", action="store_true", help="Merge structural graph with existing claims/entities")
    parser.add_argument("--seed", type=int, default=42, help="Generator random seed (default: 42)")
    args = parser.parse_args()

    mode_str = "merge" if args.merge else f"reset={args.reset}"
    print(f"Seeding structural graph for tenant '{args.tenant}' ({mode_str})...")
    res = seed_structural_graph(tenant_id=args.tenant, reset=args.reset, merge=args.merge, generator_seed=args.seed)

    print(f"Structural graph '{res['graph']}' successfully seeded in {res['elapsed_seconds']:.3f} s:")
    print("  Nodes:")
    for lbl, count in res["node_counts"].items():
        print(f"    - {lbl:12}: {count}")
    print("  Edges:")
    for edge, count in res["edge_counts"].items():
        print(f"    - {edge:12}: {count}")


if __name__ == "__main__":
    main()
