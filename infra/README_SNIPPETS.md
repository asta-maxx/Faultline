# Faultline README Snippets & Architectural Reference

## 1. Local Setup via Docker Compose

```bash
# Start FalkorDB and the FastAPI + SPA service
docker compose -f infra/docker-compose.yml up -d

# Verify system health
curl -f http://localhost:8000/health
```

Compose keeps the graph in the named volume `faultline_falkor_data`, so a fresh stack starts empty and `/health` reports `"nodes": 0, "edges": 0` (HTTP 200) until a `dump.rdb` is restored (`infra/RAILWAY.md`, section 4) or the graph is seeded.

Expected response after restoring the demo RDB:
```json
{
  "ok": true,
  "graph": "faultline:northwind",
  "nodes": 3264,
  "edges": 1567,
  "falkor": "up"
}
```

A structure-only `python -m data.seed --reset` gives `"nodes": 2826, "edges": 823` and an empty conflict queue.

---

## 2. Related Work & Differentiation

- **Graphiti**: Dynamically constructs temporal knowledge graphs using LLM extraction and vector index embeddings. *Faultline* operates directly on FalkorDB via exact Cypher graph collapse (Stage 2) and deterministic heuristic prefiltering (Stage 3), reducing pair comparisons without needing vector index infrastructure.
- **CodeScene**: Evaluates behavioral code metrics, hotspots, and team churn from git history. *Faultline* targets operational policy contradictions across disparate documents, tickets, chat messages, and ADR chains before outages occur.
- **repowise**: Maps codebase semantics and call graphs. *Faultline* models operational requirements and navigates formal ADR supersession chains (`SUPERSEDES*1..10`) to distinguish active contradictions from superseded policies.
- **Glean**: Provides enterprise-wide search and semantic retrieval across SaaS tools. *Faultline* actively detects, isolates, and scores contradictions with an organizational blast radius rather than performing passive retrieval.

---

## 3. Graph Model (CONTRACT §5 Verbatim)

### Nodes (Labels & Properties)

| Label | Properties |
| :--- | :--- |
| `Claim` | `id` (str, uuid), `text` (str), `polarity` (`"affirm"`\|`"deny"`), `subject_ref` (str), `predicate` (str, snake_case), `object` (str), `evidence_span` (str), `confidence` (float 0–1), `extracted_at` (int, epoch s) |
| `Entity` | `id` (str, slug), `name` (str), `type` (`"system"`\|`"policy"`\|`"metric"`\|`"process"`\|`"artifact"`) |
| `Document` | `id` (str), `title` (str), `path` (str), `kind` (`"runbook"`\|`"wiki"`\|`"spec"`\|`"readme"`), `updated_at` (int) |
| `Decision` | `id` (str), `ref` (str, e.g. `"ADR-88"`), `title` (str), `status` (`"accepted"`\|`"superseded"`\|`"rejected"`), `decided_at` (int) |
| `Person` | `id` (str), `name` (str), `role` (str), `active` (bool) |
| `System` | `id` (str), `name` (str), `tier` (int 1–3, 1 = most critical) |
| `Ticket` | `id` (str), `ref` (str), `title` (str), `text` (str), `state` (str), `closed_at` (int\|null) |
| `Message` | `id` (str), `channel` (str), `text` (str), `sent_at` (int) |
| `Conflict` | `id` (str), `blast_radius` (float), `status` (`"open"`\|`"resolved"`\|`"dismissed"`), `kind` (`"direct"`\|`"superseded"`\|`"undocumented"`), `found_at` (int) |

### Edges (Types, Endpoints & Properties)

| Edge | From → To | Properties |
| :--- | :--- | :--- |
| `ASSERTS` | Document\|Message\|Ticket → Claim | — |
| `ABOUT` | Claim → Entity | — |
| `CONTRADICTS` | Claim → Claim | `confidence` (float), `evidence_span` (str), `method` (str) |
| `SUPERSEDES` | Decision → Decision | newer → older |
| `CITES` | Document → Decision | — |
| `GOVERNS` | Document → System | — |
| `AUTHORED` | Person → Document\|Decision | — |
| `OWNS` | Person → System | — |
| `DERIVED_FROM` | Claim → Message\|Ticket | — (in the schema; the pipeline does not write it, message and ticket claims link through `ASSERTS`) |
| `INVOLVES` | Conflict → Claim | `side` (`"a"`\|`"b"`) |
| `RESOLVED_AS` | Conflict → Claim | `rationale` (str), `resolved_at` (int), `resolved_by` (str) |

---

## 4. Blast Radius Formula (CONTRACT §7.3 Verbatim)

Computed in Python from query results:

$$\text{blast\_radius} = \left(\sum_{s \in \text{systems}} (4 - s.\text{tier})\right) \times 2.0 + \text{doc\_count} + (\text{citing\_decisions} \times 1.5)$$

Where:
- Tier 1 weighs 3, Tier 2 weighs 2, Tier 3 weighs 1 (`sum(4 - s.tier)` over distinct governed systems).
- `doc_count`: Count of distinct sources asserting the claim (`Document`, `Message`, `Ticket`).
- `citing_decisions`: Count of distinct decisions cited (`CITES`) by any source that asserts the claim. Only documents carry `CITES`, so in practice these are the asserting documents' decisions.
- Systems are the distinct systems governed (`GOVERNS`) by any asserting source, each counted once; the sum is done in Python, never with `sum(DISTINCT ...)` in Cypher.
- `Conflict.blast_radius`: Prior to resolution, computed as $\max(\text{blast\_radius}_A, \text{blast\_radius}_B)$, never the sum. After resolution it is recomputed as the blast radius of the losing claim.

Exactly as computed in `graph/queries.py`:

```python
tier_weight  = sum(4 - s["tier"] for s in systems if s["id"])   # int
system_count = len([s for s in systems if s["id"]])
blast_radius = (tier_weight * 2.0) + doc_count + (citing_decisions * 1.5)
```

---

## 5. Contradiction Funnel (CONTRACT §6)

Measured on `faultline:northwind`, the Northwind demo slice (60 documents, 20 tickets, 20 messages, 339 claims):

| Stage | Mechanism | Measured Pairs |
| :--- | :--- | ---: |
| **1. All possible pairs** | `n*(n-1)/2`, counted, never enumerated | 57,291 |
| **2. Graph collapse** | Shared `Entity` traversal (7.1) | 1,666 |
| **3. Deterministic prefilter** | Shared `predicate` AND (differing `object` OR opposite `polarity`) | 202 |
| **4. LLM judgement** | Adjudicator, one cached call per disagreement | 159 judged |
| **Result** | `CONTRADICTS` edge and an open `Conflict` | 20 conflicts |

16 of the 20 conflicts correspond to 13 of the 14 planted contradictions (11 with the correct kind); 4 are false positives (3 from over-merged ticket "Incident" entities, 1 judge error). 12 planted contradictions reach stage 3 as the planted pair itself (claims from both planted source documents); 13 surface because a conflict can also pair one planted-source claim with a distractor document that restates the other value. The planted set was also the development set, so these numbers are optimistic.
