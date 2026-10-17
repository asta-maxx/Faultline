# Faultline README Snippets & Architectural Reference

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
| `DERIVED_FROM` | Claim → Message\|Ticket | — |
| `INVOLVES` | Conflict → Claim | `side` (`"a"`\|`"b"`) |
| `RESOLVED_AS` | Conflict → Claim | `rationale` (str), `resolved_at` (int), `resolved_by` (str) |

---

## 4. Blast Radius Formula (CONTRACT §7.3 Verbatim)

Computed in Python from query results:

$$\text{blast\_radius} = \left(\sum_{s \in \text{systems}} (4 - s.\text{tier})\right) \times 2.0 + \text{doc\_count} + (\text{citing\_decisions} \times 1.5)$$

Where:
- Tier 1 weighs 3, Tier 2 weighs 2, Tier 3 weighs 1 (`sum(4 - s.tier)` over distinct governed systems).
- `doc_count`: Count of distinct sources asserting the claim (`Document`, `Message`, `Ticket`).
- `citing_decisions`: Count of distinct decisions cited by governing documents.
- `Conflict.blast_radius`: Prior to resolution, computed as $\max(\text{blast\_radius}_A, \text{blast\_radius}_B)$.

---

## 5. Contradiction Funnel (CONTRACT §6)

| Stage | Mechanism | Measured Pairs |
| :--- | :--- | :--- |
| **1. All possible pairs** | `n*(n-1)/2`, never computed | TBD from Allen's RDB |
| **2. Graph collapse** | Shared `Entity` traversal (7.1) | TBD from Allen's RDB |
| **3. Deterministic prefilter** | Shared `predicate` AND (differing `object` OR opposite `polarity`) | TBD from Allen's RDB |
| **4. LLM judgement** | Adjudicator | TBD from Allen's RDB |
