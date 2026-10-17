# CONTRACT.md — Faultline

**This file is the interface. Everyone codes against it. It is frozen Thursday night. Changes go through Allen only, and the file is updated *before* the code that changes it.**

If you are an AI assistant reading this: this is the authoritative spec. Do not invent node labels, edge types, field names, or endpoint shapes that are not in this file. If something you need is missing, say so instead of guessing — a guess here causes a silent mismatch that surfaces two days later.

---

## 1. What we are building

**Faultline** finds where an organisation's documented knowledge contradicts itself, ranks each conflict by what is downstream of it, drafts the correction and routes it to the owner of the most critical system downstream, and records the resolution in the graph (`RESOLVED_AS`). It does not edit the source documents itself.

It is **not** a chatbot and has no "ask your docs" input. The user opens it and sees a ranked queue of conflicts the system found on its own.

Built for Graph Hacks 2026 (FalkorDB × WeMakeDevs). Entering Track 03 (Company Brain) and Track 02 (Agent Memory and Coordination). Deadline Sunday 18 Oct, we submit 20:00 IST.

**The core mechanic, which everything else serves:** naive contradiction detection is O(n²) — ~1,800 claims is ~1.6M LLM comparisons. We only compare claims that share a subject `Entity`. Measured on the Northwind demo slice: 339 claims make 57,291 pairs, the collapse leaves 1,666, the prefilter 202, and 159 are judged. Remove FalkorDB and the product is not slower, it is impossible. Protect this property in every design decision.

---

## 2. Stack

| Layer | Choice |
| --- | --- |
| Agent + API | Python 3.12, FastAPI |
| Extraction | Surveyor (`agent/surveyor.py`): constrained JSON extraction written directly onto FalkorDB, no Graphiti, no embeddings |
| Graph client | `falkordb-py`, raw Cypher, **no ORM** |
| MCP | FastMCP (same process as API) |
| Frontend | Vite + React + TypeScript (**not** Next.js) |
| Graph view | Cytoscape.js + dagre layout |
| Local | docker-compose: falkordb + app |
| Deploy | Railway, 2 services, frontend served from FastAPI |
| LLM | **Groq free tier for extraction** (measured ~0.9 s/call); **Gemini free tier for judging** (measured median ~3 s/call, but the daily quota runs out after about 30 calls, so judging overflows to Groq) |

Model names move fast and the documented defaults went stale within days — pin exact versions, never `*-latest` aliases, and verify against a live key rather than a model list. Extraction runs hundreds to thousands of calls and uses the provider with the larger quota; judging runs one call per disagreement. The binding limit is quota, not latency: Groq's free tier allows `gpt-oss-120b` 8,000 tokens per minute, so more workers only queue. Defaults: `agent.ingest` 3 workers, `agent.adjudicator` 2, a workspace audit 3 for extraction and 2 for judging.

**Zero budget.** The scarce resource is requests per day, not money. Every provider sits behind one interface, swappable by env var (`GEMINI_API_KEY`, `GROQ_API_KEY`). Everyone on the team registers their own free key — never share one, or a single quota serves four people and runs dry without anyone knowing why.

**Do not add:** Postgres, a separate vector DB, an ORM, Redis as a second store. FalkorDB is the only database. If a judge can ask "why not just SQL", we have lost.

---

## 3. Repo layout and ownership

```
/graph      schema, Cypher library, prefilter, workspace registry (registry.py)   Allen only
/agent      Surveyor, Northwind ingest (ingest.py), Adjudicator, folder audits,   Allen only
            MCP tools
/api        FastAPI app: §9 endpoints and the Reconciler (service.py),            Allen
            §9b workspaces (workspaces.py)
/web        Vite app                                                              Dev B, Allen
/data       Northwind generator, structural seed, run files                       Dev C
/infra      docker-compose, Dockerfile, deploy                                    Dev C
/fixtures   mock JSON (section 10)                                                Allen writes, B consumes
/faultline-design-system  tokens, mark, type and brand rules                      source for /web and README visuals
CONTRACT.md                                                                       Allen writes, all read
```

Short-lived branches. Allen reviews every merge. Nobody writes outside their folders.

---

## 4. Dependencies — who is blocked on what

**The design goal is that nobody blocks anybody until Saturday integration.** The fixtures in section 10 exist specifically so Dev B never waits for a real API.

| Who | Needs | From | Workaround until it lands |
| --- | --- | --- | --- |
| Everyone | this file | Allen | — (it's here) |
| Allen | FalkorDB running | nobody | `docker run -d --name faultline-falkordb -p 6380:6379 falkordb/falkordb` — host port 6380 by convention, since 6379 is often another project's Redis; 10 seconds, do not wait on /infra |
| Allen | a corpus | Dev C | hand-written 20-doc fixture, in `/fixtures/mini-corpus.json` |
| Dev B | API responses | Allen | `/fixtures/*.json` — exact shapes, section 10 |
| Dev C | graph schema | Allen | section 5, frozen |
| Dev C | nothing else | — | generator and infra are fully independent |
| Media | screenshots | Dev B | B-roll of terminal and graph work from hour one |
| Media | README content | Allen | PRD covers everything but final numbers |

**Critical path (Allen's, and only Allen's):**
`schema → ingest → claim extraction → candidate collapse → adjudication → blast radius → precedent`

Everything else runs in parallel off this file. If Allen is blocked, the project is blocked, which is why Allen touches nothing in `/web`, `/data` or `/infra`.

**The one real integration moment:** Friday night, B swaps fixtures for the live API. If shapes match this file, it takes 20 minutes. If anyone improvised a shape, it takes four hours. That is the entire reason this file exists.

---

## 5. Graph schema — FROZEN

### Nodes

| Label | Properties |
| --- | --- |
| `Claim` | `id` (str, uuid), `text` (str), `polarity` (`"affirm"`\|`"deny"`), `subject_ref` (str), `predicate` (str, snake_case), `object` (str), `evidence_span` (str), `confidence` (float 0–1), `extracted_at` (int, epoch s) |
| `Entity` | `id` (str, slug), `name` (str), `type` (`"system"`\|`"policy"`\|`"metric"`\|`"process"`\|`"artifact"`) |
| `Document` | `id` (str), `title` (str), `path` (str), `kind` (`"runbook"`\|`"wiki"`\|`"spec"`\|`"readme"`), `updated_at` (int) |
| `Decision` | `id` (str), `ref` (str, e.g. `"ADR-88"`), `title` (str), `status` (`"accepted"`\|`"superseded"`\|`"rejected"`), `decided_at` (int) |
| `Person` | `id` (str), `name` (str), `role` (str), `active` (bool) |
| `System` | `id` (str), `name` (str), `tier` (int 1–3, 1 = most critical) |
| `Ticket` | `id` (str), `ref` (str), `title` (str), `text` (str), `state` (str), `closed_at` (int\|null) |
| `Message` | `id` (str), `channel` (str), `text` (str), `sent_at` (int) |
| `Conflict` | `id` (str), `blast_radius` (float), `status` (`"open"`\|`"resolved"`\|`"dismissed"`), `kind` (`"direct"`\|`"superseded"`\|`"undocumented"`), `found_at` (int) |

### Edges

| Edge | From → To | Properties |
| --- | --- | --- |
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

`DERIVED_FROM` is part of the schema, but the pipeline does not write it: a claim extracted from a `Message` or `Ticket` is linked to it by `ASSERTS`, exactly like a document's claim.

### Constraints and indexes — run once at startup

FalkorDB does **not** accept Neo4j's `CREATE CONSTRAINT ... ASSERT` syntax. Use the native command, which is issued on the Redis connection rather than as Cypher:

```
GRAPH.CONSTRAINT CREATE faultline:northwind UNIQUE NODE Claim PROPERTIES 1 id
```

…once per label for `Claim`, `Entity`, `Document`, `Decision`, `Person`, `System`, `Conflict`. Constraint creation is asynchronous — poll `CALL db.constraints()` (there is no `GRAPH.CONSTRAINT LIST`) until each reaches `OPERATIONAL` before loading data, or the uniqueness guarantee isn't in force yet. Must be idempotent: re-running creates nothing and errors on nothing.

Indexes, as Cypher:

```cypher
CREATE INDEX FOR (c:Claim)    ON (c.confidence);
CREATE INDEX FOR (c:Claim)    ON (c.predicate);
CREATE INDEX FOR (e:Entity)   ON (e.name);
CREATE INDEX FOR (k:Conflict) ON (k.status);
CREATE INDEX FOR (k:Conflict) ON (k.blast_radius);
```

**Entity resolution rule:** aliases are normalised at ingest so there is exactly **one** `Entity` per real subject. No `SAME_AS` edge exists. This keeps the candidate query an exact shared-node match instead of a variable-length walk, which is both faster and far easier to explain to a judge.

**Multi-tenancy:** one FalkorDB graph per tenant, named `faultline:{tenant_id}`. Default tenant is `northwind`. Never add a `tenant` property to nodes — isolation is at the graph level, which is the FalkorDB multigraph feature we want to be seen using.

---

## 6. Claim extraction schema

The Surveyor emits this. Constrained, never free-form — free-form extraction is the single biggest risk to the demo.

```json
{
  "claims": [
    {
      "text": "Failed writes to the payments ledger are retried up to three times.",
      "polarity": "affirm",
      "subject_ref": "payments-ledger",
      "subject_name": "Payments Ledger",
      "subject_type": "system",
      "predicate": "retry_policy",
      "object": "3 attempts",
      "confidence": 0.91,
      "evidence_span": "retried up to three times",
      "source_doc_id": "doc-0141",
      "derived_from": null
    }
  ]
}
```

Rules the extractor must follow:
- One assertion per claim. A sentence with two assertions produces two claims.
- `predicate` is a snake_case verb phrase, reused across claims about the same aspect. This is what makes two claims comparable.
- `confidence` below **0.65** is dropped at ingest and never enters the graph.
- `evidence_span` must be a literal substring of the source document. If it is not, drop the claim.
- `subject_ref` is a slug; the ingest maps it to exactly one `Entity`.

### The four-stage funnel

This is the product. Two of the four stages cost nothing: stage 1 is counted, never enumerated, and only stage 4 calls a model.

| Stage | Mechanism | Order of magnitude |
| --- | --- | --- |
| 1. All possible pairs | `n*(n-1)/2`, never computed | ~10⁶ |
| 2. **Graph collapse** | shared `Entity` traversal (7.1) | ~10³ |
| 3. **Deterministic prefilter** | shared `predicate` AND (differing `object` OR opposite `polarity`) | ~10² |
| 4. LLM judgement | Adjudicator | ~10² calls |

**The counts above are orders of magnitude, not targets.** Stage 2's real size depends on how claims concentrate across entities — a corpus where a few entities carry many claims produces far more pairs than a uniform one. Measure and report what the corpus actually yields. Never tune the data to hit a number from this document; a 1,000× reduction is as good a story as a 5,000× one, and an honest measured figure survives a judge's follow-up question.

Stage 3 runs in Python with no model call. Instrument all four numbers and surface them in `/stats` — they are the headline of the demo and the proof that FalkorDB is load-bearing.

**LLM response caching is mandatory, not an optimisation.** Hash the input (model, operation, prompt, content and parameters), cache the response to disk (`cache/` at the repo root, `/cache` in the Docker image, `FAULTLINE_CACHE_DIR` overrides), never pay for the same call twice. Extraction will be re-run many times while tuning prompts; without this you burn a day's free quota by Friday. Build the cache before the first real extraction run. `/cache` is gitignored.

---

## 7. Core Cypher — these are the queries judges will read

### 7.1 Candidate collapse — the one that matters

```cypher
// Every pair of claims sharing a subject, excluding pairs already judged.
MATCH (a:Claim)-[:ABOUT]->(e:Entity)<-[:ABOUT]-(b:Claim)
WHERE a.id < b.id
  AND a.confidence >= $floor
  AND b.confidence >= $floor
  AND NOT (a)-[:CONTRADICTS]-(b)
  AND NOT (a)<-[:INVOLVES]-(:Conflict)-[:INVOLVES]->(b)
RETURN a.id AS a_id, a.text AS a_text, a.predicate AS a_pred,
       a.object AS a_obj, a.polarity AS a_pol,
       b.id AS b_id, b.text AS b_text, b.predicate AS b_pred,
       b.object AS b_obj, b.polarity AS b_pol,
       e.id AS entity_id, e.name AS entity
ORDER BY e.id
```

**Three things about this query, each verified against FalkorDB rather than assumed:**

1. **`EXISTS(pattern)` is rejected** — FalkorDB refuses traversal patterns as arguments to `exists()`. Use the bare pattern predicate `NOT (a)-[:R]-(b)` as written.
2. **`a.id < b.id` is load-bearing and must never be removed.** The shared-entity pattern will match `a` and `b` to the *same* claim, so without it the result contains self-pairs as well as reversed duplicates. Dropping it took a 53-row result to 136.
3. **The exclusion is "a Conflict involving *both* claims"**, not "either claim appears in any Conflict". The second form silently hides unjudged pairs whenever each side happens to belong to some other conflict.

Instrument this. Log `n*(n-1)/2` and the actual row count every run. **Those numbers are the headline of the demo video — report what the real corpus produces, never a figure from this document.**

### 7.2 Current claim — adjudication by traversal, not timestamp

```cypher
// From any decision, walk SUPERSEDES backwards to the one nothing supersedes.
MATCH (start:Decision {id: $decision_id})
OPTIONAL MATCH (live:Decision)-[:SUPERSEDES*1..10]->(start)
WHERE NOT (:Decision)-[:SUPERSEDES]->(live)
RETURN coalesce(live, start) AS current,
       coalesce(length(shortestPath((live)-[:SUPERSEDES*]->(start))), 0) AS chain_depth
```

`chain_depth` is `0` when the decision is already current — never null.

This is why a document with a *newer* `updated_at` can still be wrong. Timestamp logic gets that case backwards; this does not. Demo case 2 depends on it.

### 7.3 Blast radius

```cypher
MATCH (c:Claim {id: $claim_id})
OPTIONAL MATCH (src)-[:ASSERTS]->(c)
OPTIONAL MATCH (src)-[:GOVERNS]->(s:System)
OPTIONAL MATCH (src)-[:CITES]->(dec:Decision)
OPTIONAL MATCH (p:Person)-[:OWNS]->(s)
RETURN
  count(DISTINCT src) AS doc_count,
  count(DISTINCT dec) AS citing_decisions,
  collect(DISTINCT {id: s.id, tier: s.tier}) AS systems,
  collect(DISTINCT {id: p.id, name: p.name}) AS owners
```

**Do not use `sum(DISTINCT 4 - s.tier)`** — it deduplicates equal values, so two tier-1 systems contribute 3 instead of 6. Return the distinct systems and sum in Python. Drop `{id: null}` entries from both collections (`OPTIONAL MATCH` produces them when a document governs nothing or a system has no owner).

Score, computed in Python:

```python
tier_weight  = sum(4 - s["tier"] for s in systems if s["id"])   # int
system_count = len([s for s in systems if s["id"]])
blast_radius = (tier_weight * 2.0) + doc_count + (citing_decisions * 1.5)
```

Tier 1 weighs 3, tier 2 weighs 2, tier 3 weighs 1. `tier_weight` and `system_count` are ints in the MCP response; `blast_radius` is a float. Document the formula in the README exactly as written — a judge asking "where does that number come from" must get a formula, not a shrug.

`src` is deliberately untyped so `Document`, `Message` and `Ticket` all match — a claim whose only source is a chat message would otherwise score zero. Messages and tickets govern no systems, so they contribute `0` to `tier_weight`, which is correct: an undocumented claim is dangerous because of what the *other* side governs, not itself.

**Rolling up to a Conflict:** before resolution we don't know which claim is wrong, so `Conflict.blast_radius` is the **maximum** of the two sides, not their sum — summing double-counts whenever both claims sit in the same document. After resolution, recompute it as the blast radius of the *losing* claim, which is the real damage.

### 7.4 Precedent — the Track 02 claim

```cypher
// Has a conflict between these two subjects already been settled?
MATCH (k:Conflict)-[:INVOLVES]->(a:Claim)-[:ABOUT]->(e:Entity)
MATCH (k)-[:RESOLVED_AS]->(winner:Claim)
WHERE e.id = $entity_id AND k.status = 'resolved'
RETURN DISTINCT k.id AS conflict_id, winner.id AS winner_id,
       winner.text AS winner_text, k.found_at AS settled_at
ORDER BY k.found_at DESC
LIMIT 5
```

The Adjudicator calls this **before** judging a pair. If a settled winner is one of the two claims, the pair is not judged and not re-flagged. A disagreement that already has a `Conflict` is skipped before this check. There is no escalation step: a claim whose text changed is a new claim and is judged as a new pair. `agent.ingest` and a workspace audit both rebuild their graph, so precedent lasts only as long as the graph. `GET /conflicts/{id}` returns the settled conflicts about the same Entity as `precedent` (§9, v7), excluding the conflict itself and dated by `RESOLVED_AS.resolved_at` rather than `found_at`.

### 7.5 Traversal path for the UI

```cypher
// The subgraph behind one conflict. Capped — never return the whole graph.
MATCH (k:Conflict {id: $conflict_id})-[:INVOLVES]->(c:Claim)
OPTIONAL MATCH (d:Document)-[:ASSERTS]->(c)
OPTIONAL MATCH (d)-[:GOVERNS]->(s:System)
OPTIONAL MATCH (d)-[:CITES]->(dec:Decision)
OPTIONAL MATCH (dec)<-[:SUPERSEDES*0..3]-(sup:Decision)
OPTIONAL MATCH (c)-[:DERIVED_FROM]->(src)
RETURN c, d, s, dec, sup, src
LIMIT 40
```

This query sees only `Document` sources, and `DERIVED_FROM` is never written, so on its own it misses claims asserted by a message or ticket. `GET /conflicts/{id}` (`build_path` in `api/service.py`) adds the claims' `Entity`, every source that `ASSERTS` either claim, the `SUPERSEDES` edges between the decisions it returns, and the routed owner with `OWNS` edges, still capped at 40 nodes (§9).

---

## 8. MCP tool signatures

Served by FastMCP from the API process over streamable HTTP at `/mcp/` (`/mcp` redirects there). Every tool also takes an optional `workspace: str = "northwind"` argument, not repeated below, and reads `faultline:{workspace}`; an id that is not a workspace slug returns an error.

All tools return JSON. Errors return `{"error": "<message>"}` as a normal tool result — the agent handles them, not the transport.

```
find_candidates(entity_id: str | null, floor: float = 0.65, limit: int = 200)
  -> {"pairs": [{"a_id","a_text","a_pred","a_obj","a_pol",
                 "b_id","b_text","b_pred","b_obj","b_pol","entity_id","entity"}],
      "naive_pair_count": int, "collapsed_pair_count": int,
      "prefiltered_pair_count": int}

judge_pair(a_id: str, b_id: str)
  -> {"verdict": "contradicts" | "compatible" | "unclear",
      "confidence": float, "evidence_span": str, "reasoning": str}

blast_radius(claim_id: str)
  -> {"score": float, "doc_count": int, "system_count": int,
      "citing_decisions": int, "tier_weight": int,
      "owners": [{"id","name"}]}

current_claim(entity_id: str)
  -> {"current_decision": {"id","ref","title","decided_at"} | null,
      "chain_depth": int, "superseded": [{"id","ref","title"}]}

precedent_for(a_id: str, b_id: str)
  -> {"found": bool, "conflict_id": str | null, "winner_id": str | null,
      "winner_text": str | null, "settled_at": int | null}

route_owner(conflict_id: str)
  -> {"owner": {"id","name","role"} | null, "path": [{"id","label","type"}],
      "reason": str}
```

Notes on the live tools:

- `find_candidates` counts the **unjudged** pairs (§7.1, which excludes pairs already joined by `CONTRADICTS` or a `Conflict`), so its `collapsed_pair_count` and `prefiltered_pair_count` shrink as the Adjudicator works. `/stats` counts **all** shared-Entity pairs and stays at the corpus's funnel.
- `current_claim` starts from the decisions cited by documents that assert a claim about the entity, walks `SUPERSEDES` to the decisions nothing supersedes, and returns the most recently decided of them. Its `chain_depth` is the number of decisions that one supersedes, directly or through the chain, which is also the length of `superseded`. That is not §7.2's `chain_depth`, the distance from one given start decision.
- `precedent_for` returns the settled conflict whose winner is `a_id` or `b_id` if there is one, otherwise the newest settled conflict about `a_id`'s entity.

---

## 9. HTTP API

Every endpoint except `/health` is served under the `/api` prefix (`GET /api/conflicts`, and so on), so the SPA can own the `/conflicts` and `/resolved` routes in the browser. `/health` is served at both `/health` and `/api/health`.

```
GET  /health
  -> {"ok": bool, "graph": str, "nodes": int, "edges": int, "falkor": "up"|"down"}

GET  /conflicts?status=open&limit=20
  -> {"conflicts": [Conflict], "total": int, "stats": Stats}

GET  /conflicts/{id}
  -> {"conflict": Conflict, "path": GraphPath}

POST /conflicts/{id}/resolve
  body {"winner_claim_id": str, "rationale": str, "resolved_by": str}
  -> {"ok": true, "conflict": Conflict}

POST /conflicts/{id}/draft
  -> {"correction": str, "owner": {"id","name","role"}, "ticket": {"title","body"}}
  # 422 when no Person OWNS a system downstream of either side (always so for folder workspaces)

POST /conflicts/{id}/dismiss                       # v7
  body {"rationale": str, "dismissed_by": str}
  -> {"ok": true, "conflict": Conflict}
  # 404 unknown conflict; 409 if it is not open; 422 if rationale or dismissed_by is empty

GET  /stats
  -> Stats

POST /reingest            # token-gated, NEVER on the default demo path
  header X-Reingest-Token
  -> {"job_id": str}
```

### Types

```ts
type Conflict = {
  id: string
  kind: "direct" | "superseded" | "undocumented"
  status: "open" | "resolved" | "dismissed"
  blast_radius: number
  found_at: number
  entity: { id: string; name: string; type: string }
  claims: {
    side: "a" | "b"
    id: string
    text: string
    confidence: number
    evidence_span: string
    state: "live" | "contradicted" | "superseded"
    source: { doc_id: string; title: string; path: string; updated_at: number }
  }[]
  impact: { doc_count: number; system_count: number; systems: string[] }
  owner: { id: string; name: string; role: string } | null
  // v5, optional: the CONTRADICTS edge between the two claims, null if none
  judgement?: { method: string; confidence: number; evidence_span: string } | null
  // v5, optional: the RESOLVED_AS edge, null unless status is "resolved"
  resolution?: { winner_claim_id: string; rationale: string; resolved_at: number; resolved_by: string } | null
  // v7, optional: set by POST /dismiss, null unless status is "dismissed". Stored on the Conflict
  // node as dismiss_rationale, dismissed_by and dismissed_at (epoch s): the only Conflict
  // properties beyond §5, written only on dismissal.
  dismissal?: { rationale: string; dismissed_by: string; dismissed_at: number } | null
}

// v7, GET /conflicts/{id} only: the §7.4 precedent for this conflict's Entity. `found` is
// false when nothing about the Entity has been settled. When a settled winner is one of this
// conflict's claims, the Adjudicator would not have re-flagged the pair.
type Precedent = {
  found: boolean
  settled: { conflict_id: string; winner_id: string; winner_text: string; settled_at: number }[]
}
// ConflictDetailResponse: { conflict: Conflict, path: GraphPath, precedent?: Precedent }

type GraphPath = {
  nodes: { id: string; label: string; type: string; state?: "live"|"contradicted"|"superseded"; at?: number }[]
  edges: { source: string; target: string; type: string }[]
}

type Stats = {
  claims: number
  documents: number
  entities: number
  naive_pair_count: number       // stage 1 — n*(n-1)/2
  collapsed_pair_count: number   // stage 2 — shared-Entity traversal
  prefiltered_pair_count: number // stage 3 — deterministic prefilter
  judged_pair_count: number      // stage 4 — actual LLM calls
  conflicts_open: number
  conflicts_resolved: number
}
```

`node.type` in `GraphPath` is the node label lowercased (`claim`, `entity`, `document`, `decision`, `system`, `person`, `message`, `ticket`). B maps those to icons.

**v5 addition, optional:** a `GraphPath` node may carry `at` (int, epoch seconds): its own §5 date (`Document.updated_at`, `Decision.decided_at`, `Message.sent_at`, `Ticket.closed_at`), and for a `Claim` the date of the source that asserts it. `System`, `Entity` and `Person` have no date in §5 and never carry `at`. The path also includes the claims' `Entity` (with `ABOUT` edges) and the conflict's routed owner (with `OWNS` edges to systems in the path); still capped at 40 nodes.

**Behaviour of the live API** (`api/main.py`, `api/service.py`):

- `GET /conflicts`: `status` defaults to every status (`all` or an empty value mean the same); `limit` defaults to 50, minimum 1, maximum 200. `total` counts every conflict with that status, not only the returned page.
- `POST /conflicts/{id}/resolve`: 404 for an unknown conflict; 409 if it is not open; 422 if `winner_claim_id` is not one of its two claims, or `rationale` or `resolved_by` is empty. On success the conflict's `blast_radius` becomes the losing claim's (§7.3).
- `POST /conflicts/{id}/draft`: 404 for an unknown conflict; 422 when there is no owner to route to. It makes one judge-model call (cached) and writes nothing to the graph.
- `POST /reingest` (served at `/api/reingest`): 503 when `REINGEST_TOKEN` is not set on the server; 403 when the `X-Reingest-Token` header is missing or wrong. The job re-runs `agent.ingest` and `agent.adjudicator`, which rebuilds the graph.
- `Stats.judged_pair_count` is the number of stage-3 pairs whose judgement is in the LLM cache **on the machine serving the API**, not a count of calls made. On a machine without the cache, it is lower than the number the funnel actually judged. `/stats` is cached for 10 s.
- With `FAULTLINE_FIXTURES=1` only `GET /stats`, `GET /conflicts` and `GET /conflicts/{id}` are served, from `fixtures/`; the write endpoints and §9b are not registered.

---

### 9b. Workspaces, sources and audits (v6)

A workspace is one FalkorDB graph, `faultline:{workspace_id}`: the multigraph is the isolation, there is no tenant property anywhere. `workspace_id` is a slug of the name (`[a-z0-9-]`). No auth, no accounts: a workspace is created and used at once.

Workspace, source and audit records live in one more graph in the same instance, **`faultline:_registry`**. Its labels (`Workspace`, `Source`, `AuditRun`) and edges (`HAS_SOURCE`, `RAN`) exist only there and never appear in a workspace graph; §5 still governs every workspace graph. The registry is not a second database: same FalkorDB, one more graph.

The §9 conflict and stats endpoints, including resolve, dismiss and draft, take an optional `?workspace=<id>` (default `northwind`); an unknown or malformed id is a 404. The `northwind` workspace is registered automatically whenever the registry is read and `faultline:northwind` exists without a `Workspace` record.

```
GET    /api/workspaces                      -> [Workspace]
POST   /api/workspaces          {name}       -> Workspace            409 if the id exists
GET    /api/workspaces/{id}/sources         -> [Source]
POST   /api/workspaces/{id}/sources  {kind, location, token?} -> Source   422 if a folder is missing or outside FAULTLINE_SOURCE_ROOT
DELETE /api/workspaces/{id}/sources/{source_id} -> {ok: true}
POST   /api/workspaces/{id}/audit           -> {run_id}             409 if an audit is running, 422 if no readable source
GET    /api/audits/{run_id}                 -> AuditRun
```

```ts
type Workspace = {
  id: string; name: string; graph: string      // graph = "faultline:{id}"
  sources: number; documents: number; claims: number
  conflicts: number                            // open conflicts
  last_audit: number | null                    // epoch s, end of the latest finished audit
  latest_run: { run_id: string; status: "running" | "done" | "failed"; started_at: number } | null
                                               // the most recent audit of any status; open /audit/{run_id} for it
}

type Source = {
  id: string; kind: "folder" | "git"; location: string
  docs: number | null                          // readable files found when scanned; null if never scanned
  claims: number | null                        // claims extracted from it by the latest audit
  status: "ready" | "unsupported" | "missing"  // "unsupported": only git sources added before v8
  message: string | null                       // plain-language reason for any status other than "ready"
  has_token: boolean                           // a token was supplied; the token itself is never stored
  added_at: number; last_read_at: number | null
}

type AuditRun = {
  run_id: string; workspace_id: string
  status: "running" | "done" | "failed"
  stage: string | null                         // name of the active stage
  stages: {
    name: "READING SOURCES" | "EXTRACTING CLAIMS" | "BUILDING GRAPH" | "COLLAPSING CANDIDATES" | "JUDGING PAIRS"
    state: "pending" | "active" | "done" | "failed"
    count: number | null; unit: string          // documents, claims, possible pairs, candidate pairs, pairs judged
    detail: string | null                       // e.g. "202 after prefilter", "20 contradictions"
    started_at: number | null; ended_at: number | null
  }[]
  current: string | null                       // file or pair being processed right now
  summary: { documents: number; claims: number; pairs_compared: number; judged: number; contradictions: number } | null
  error: string | null
  started_at: number; ended_at: number | null
}
```

**Git sources (v8).** `POST …/sources {kind: "git", location, token?}` clones the repository when it is added: shallow (latest commit), symlinks checked out as plain files, LFS objects not fetched, at most `FAULTLINE_GIT_TIMEOUT_S` seconds (default 120) and `FAULTLINE_GIT_MAX_MB` (default 200) on disk. The URL must be `https://` on a host in `FAULTLINE_GIT_HOSTS` (default `github.com,gitlab.com,bitbucket.org`) and carry no credentials. A failed clone is a 422 with git's own message and no source is created. The token, when given, is passed to that one clone through the environment and never stored or logged; `has_token` records only that one was given. An audit fetches the latest commit again for public repositories; when that fails (a private repository, whose token is gone) it reads the copy cloned when the source was added and says so in the READING SOURCES detail. Nothing in a repository is executed: only `.md`, `.markdown` and `.txt` files are read, and symlinks are never followed.

**Folder sources** read a folder on the machine running the API, so they work only when you run Faultline yourself; a hosted deployment cannot see a visitor's computer. `FAULTLINE_ALLOW_FOLDERS=0` refuses them with a 422 that says so (the hosted demo sets it); `FAULTLINE_SOURCE_ROOT` confines them when allowed.

Stage counts: documents read; claims kept; `n·(n−1)/2` possible pairs once the claims are in the graph; pairs sharing an Entity (§7.1); pairs judged. Folder sources read `.md`, `.markdown` and `.txt` files under the folder. A file's document id is its file name without extension when that is unique, its title is the first `#` heading or the file name, `updated_at` is the file's modification time.

Error cases not shown above: every `{id}` route returns 404 for an unknown or malformed workspace id. `POST /workspaces` returns 422 when the name has no letter or digit. `POST .../sources` returns 422 for an empty location or a `kind` other than `folder` or `git`; when `FAULTLINE_SOURCE_ROOT` is unset, any existing folder on the server is accepted. `DELETE .../sources/{source_id}` and `GET /audits/{run_id}` return 404 when not found. A folder with no readable files is accepted as a source and fails the audit in READING SOURCES.

An audit **rebuilds the workspace graph from scratch** (sources, claims, entities, then the funnel), so conflicts resolved or dismissed in that workspace before a re-audit are not kept. A run still marked `running` when no server thread owns it (the server restarted mid-audit) is reported and saved as `failed`.

## 10. Fixtures — Dev B starts against these, today

Allen writes these before anything else. They are the real shapes, not sketches.

```
/fixtures/conflicts.json     GET /conflicts          (6 conflicts, all 3 kinds)
/fixtures/conflict-01.json   GET /conflicts/{id}     (with full GraphPath)
/fixtures/stats.json         GET /stats
/fixtures/mini-corpus.json   20 docs, for Allen's extraction before C's generator lands
```

Current state: the live API is the default, and these files are served only when the API runs with `FAULTLINE_FIXTURES=1` (three endpoints, §9). The numbers in `stats.json`, and the copy embedded in `conflicts.json`, are placeholders, not measurements (`fixtures/README.md`). `mini-corpus.json` holds 20 documents, 3 messages and 1 ticket, with 7 planted contradictions as an answer key. They predate v5 and v7, so they carry none of the optional `judgement`, `resolution` or `precedent` fields.

B built against these until the live API landed. **If the live API disagrees with a fixture, the API is wrong and Allen fixes it** — not the frontend. That rule is what makes integration 20 minutes instead of four hours.

---

## 11. Rules

1. FalkorDB is the only **database**. No Postgres, no vector DB, no second store of record. The `/cache` directory is not a database — it is memoised LLM responses on disk and is required by rule 7.
2. Raw Cypher, no ORM. Judges read our queries.
3. The UI never renders the full graph — only a traversal path, cap 40 nodes.
4. Extraction never runs on the default demo path. Graph is pre-built and shipped as an RDB dump.
5. Confidence floor 0.65. Nothing below it enters the graph.
6. `evidence_span` must be a literal substring of its source, always. Drop any claim where it is not.
7. Every LLM call is cached to disk by input hash. No exceptions — free-tier quota is the binding constraint.
8. `CONTRADICTS.method` records the model that judged the pair, e.g. `"gemini-3.5-flash"`. Provenance is what this product is about; our own edges should carry it too.
9. Colour never carries meaning alone — every state has a glyph and a word.
10. Secrets in env vars. The repo goes public at submission.
11. This file is updated **before** the code that changes it.
12. Everyone must be able to explain the schema, the queries and the architecture. Competition rule 12, and judges do ask.

---

## 12. Cut order when we slip

1. Real-repo ingest
2. Precedent memory (and with it the Track 02 entry)
3. Reconciler actions
4. Blast-radius ranking

**Never cut:** contradiction detection, the traversal-path UI, the naive-vs-collapsed benchmark, the demo video, the README graph model.