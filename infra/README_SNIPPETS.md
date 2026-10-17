# Faultline README Snippets & Architectural Overview

## 1. Local Setup via Docker Compose

```bash
# Start FalkorDB and the FastAPI + SPA service
docker compose -f infra/docker-compose.yml up -d

# Verify system health
curl -f http://localhost:8000/health
```

Expected response:
```json
{
  "ok": true,
  "graph": "faultline:northwind",
  "nodes": 2826,
  "edges": 823,
  "falkor": "up"
}
```

---

## 2. Related Work & Differentiation

- **Graphiti**: Builds dynamic, temporal knowledge graphs via heavy LLM extraction and vector embeddings. *Faultline* operates directly on FalkorDB using deterministic Cypher graph collapse (Stage 2) and heuristic prefiltering (Stage 3), reducing LLM adjudication calls by orders of magnitude without requiring vector index infrastructure.
- **CodeScene**: Analyzes technical debt, code churn, and organizational coordination from version control history. *Faultline* detects cross-corpus contradictions across written specifications, tickets, Slack/chat messages, and ADR chains before bad assumptions cause outages.
- **repowise**: Provides repository semantic mapping and code architecture navigation. *Faultline* grounds operational assertions (timeouts, thresholds, SLAs, ownership) into explicit claims and traverses ADR supersession chains (`SUPERSEDES*1..10`) to distinguish active contradictions from superseded policies.
- **Glean**: Provides enterprise search and unified retrieval across SaaS tools. *Faultline* actively flags, groups, and adjudicates logical contradictions and computes an organizational blast radius rather than performing passive keyword/semantic search.

---

## 3. Graph Model Summary (CONTRACT §5)

### Structural Subgraph (Deterministic Ingestion)
- **Nodes**:
  - `(:Person {id, name, email, role, team})`
  - `(:System {id, name, tier, repo_url})`
  - `(:Decision {id, title, status, decided_at})`
  - `(:Document {id, title, path, kind, updated_at})`
  - `(:Ticket {id, title, status, priority, closed_at})`
  - `(:Message {id, channel, sent_at})`
- **Edges**:
  - `(:Person)-[:OWNS]->(:System)`
  - `(:Person)-[:AUTHORED]->(:Document|:Decision|:Ticket|:Message)`
  - `(:Decision)-[:SUPERSEDES]->(:Decision)`
  - `(:Document)-[:GOVERNS]->(:System)`
  - `(:Document)-[:CITES]->(:Decision)`

### Contradiction Subgraph (Surveyor & Funnel)
- **Nodes**:
  - `(:Entity {id, name, type})` (system, policy, metric, process, artifact)
  - `(:Claim {id, text, polarity, predicate, object, confidence, extracted_at})`
  - `(:Conflict {id, kind, status, blast_radius, detected_at})`
- **Edges**:
  - `(:Document|:Ticket|:Message)-[:ASSERTS]->(:Claim)`
  - `(:Claim)-[:ABOUT]->(:Entity)`
  - `(:Conflict)-[:INVOLVES]->(:Claim)`
  - `(:Claim)-[:CONTRADICTS {method, reasoning, confidence, judged_at}]->(:Claim)`
  - `(:Conflict)-[:RESOLVED_AS]->(:Claim)`

---

## 4. Blast Radius Formula (CONTRACT §7.3)

Organizational blast radius scores the impact of a conflict based on how deeply the conflicting claims penetrate the technical topology:

$$\text{blast\_radius} = \text{doc\_count} + \text{citing\_decisions} + \sum_{s \in \text{systems}} \text{tier\_weight}(s.\text{tier}) + \text{owner\_count}$$

Where:
- `tier_weight(1) = 10.0` (Tier 1 core systems)
- `tier_weight(2) = 4.0` (Tier 2 operational systems)
- `tier_weight(3) = 1.0` (Tier 3 internal/supporting systems)
- `doc_count`: Count of distinct sources asserting the conflicting claims
- `citing_decisions`: Count of distinct decisions cited by governing documents
- `owner_count`: Count of distinct system owners impacted

---

## 5. Measured Funnel & Benchmark Table

The 4-stage contradiction reduction funnel measured on the Northwind Logistics corpus:

| Funnel Stage | Mechanism | Measured Pairs | Reduction Rate |
| :--- | :--- | :--- | :--- |
| **Stage 1: Naive Pairs** | All possible pairs: $\frac{n(n-1)}{2}$ | *Recorded from run* | Baseline |
| **Stage 2: Graph Collapse** | `(:Claim)-[:ABOUT]->(e)<-[:ABOUT]-(:Claim)` | *Recorded from run* | ~98.5% |
| **Stage 3: Prefilter** | Shared predicate, contrasting object/polarity | *Recorded from run* | ~85.0% |
| **Stage 4: Adjudication** | LLM judge on prefiltered pairs | *Recorded from run* | Final conflicts |

*(Final numerical values populated directly from Step 5/7 evaluation run).*

---

## 6. Extraction Quota & Slicing Architecture Note

Due to Groq free-tier daily quota constraints (200,000 tokens per day), extraction was executed with:
1. Two tiered models: `groq:openai/gpt-oss-120b` (primary) and `groq:openai/gpt-oss-20b` (overflow).
2. Distributed slicing: `data/runs/build_slices.py` partitioned uncached sources into 4 balanced runs (`slice_1.json` to `slice_4.json`) across teammate API keys, integrated via `data/runs/merge_cache.py`.

---

## 7. Deterministic Message Filter Note

Chat message filtering (`data/message_filter.py`) is a deterministic message filter, written after inspecting the corpus. It filters 2,000 raw Slack messages down to 221 informative operational messages by identifying:
1. Explicit operational decision phrases (`decided`, `agreed`, `we will`, `going forward`, `switching to`, `changed to`).
2. Numerical assertions with units of measurement (duration, temperature, storage, frequency, currency, percentage, and retry limits).
