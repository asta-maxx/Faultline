# CONTRACT.md — Faultline

**This file is the interface. Everyone codes against it. It is frozen Thursday night. Changes go through Allen only, and the file is updated *before* the code that changes it.**

If you are an AI assistant reading this: this is the authoritative spec. Do not invent node labels, edge types, field names, or endpoint shapes that are not in this file. If something you need is missing, say so instead of guessing — a guess here causes a silent mismatch that surfaces two days later.

---

## 1. What we are building

**Faultline** finds where an organisation's documented knowledge contradicts itself, ranks each conflict by what is downstream of it, and repairs it.

It is **not** a chatbot and has no "ask your docs" input. The user opens it and sees a ranked queue of conflicts the system found on its own.

Built for Graph Hacks 2026 (FalkorDB × WeMakeDevs). Entering Track 03 (Company Brain) and Track 02 (Agent Memory and Coordination). Deadline Sunday 18 Oct, we submit 20:00 IST.

**The core mechanic, which everything else serves:** naive contradiction detection is O(n²) — ~1,800 claims is ~1.7M LLM comparisons. We only compare claims that share a subject `Entity`, which collapses it to ~340. Remove FalkorDB and the product is not slower, it is impossible. Protect this property in every design decision.

---

## 2. Stack

| Layer | Choice |
| --- | --- |
| Agent + API | Python 3.12, FastAPI |
| Extraction | Graphiti onto FalkorDB |
| Graph client | `falkordb-py`, raw Cypher, **no ORM** |
| MCP | FastMCP (same process as API) |
| Frontend | Vite + React + TypeScript (**not** Next.js) |
| Graph view | Cytoscape.js + dagre layout |
| Local | docker-compose: falkordb + app |
| Deploy | Railway, 2 services, frontend served from FastAPI |
| LLM | **Groq free tier for extraction** (measured ~0.9 s/call); **Gemini free tier for judging** (measured ~22 s/call, so parallelise) |

Model names move fast and the documented defaults went stale within days — pin exact versions, never `*-latest` aliases, and verify against a live key rather than a model list. Extraction runs thousands of calls and must use the fast provider; judging runs hundreds and can afford the slow one. Both must run concurrently (10–20 workers) — serial extraction at 22 s/call does not finish.

**Zero budget.** The scarce resource is requests per day, not money. Every provider sits behind one interface, swappable by env var (`GEMINI_API_KEY`, `GROQ_API_KEY`). Everyone on the team registers their own free key — never share one, or a single quota serves four people and runs dry without anyone knowing why.

**Do not add:** Postgres, a separate vector DB, an ORM, Redis as a second store. FalkorDB is the only database. If a judge can ask "why not just SQL", we have lost.

---

## 3. Repo layout and ownership

```
/graph      schema, Cypher library, algorithms      Allen only
/agent      Surveyor, Adjudicator, Reconciler, MCP  Allen only
/web        Vite app                                Dev B
/data       Northwind generator, ingest             Dev C
/infra      docker-compose, Dockerfile, deploy      Dev C
/fixtures   mock JSON (section 10)                  Allen writes, B consumes
CONTRACT.md                                         Allen writes, all read
```

Short-lived branches. Allen reviews every merge. Nobody writes outside their folders.

---

## 4. Dependencies — who is blocked on what

**The design goal is that nobody blocks anybody until Saturday integration.** The fixtures in section 10 exist specifically so Dev B never waits for a real API.

| Who | Needs | From | Workaround until it lands |
| --- | --- | --- | --- |
| Everyone | this file | Allen | — (it's here) |
| Allen | FalkorDB running | nobody | `docker run -p 6379:6379 falkordb/falkordb` — 10 seconds, do not wait on /infra |
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

### The three-stage funnel

This is the product. Two of the three stages cost nothing.

| Stage | Mechanism | Order of magnitude |
| --- | --- | --- |
| 1. All possible pairs | `n*(n-1)/2`, never computed | ~10⁶ |
| 2. **Graph collapse** | shared `Entity` traversal (7.1) | ~10³ |
| 3. **Deterministic prefilter** | shared `predicate` AND (differing `object` OR opposite `polarity`) | ~10² |
| 4. LLM judgement | Adjudicator | ~10² calls |

**The counts above are orders of magnitude, not targets.** Stage 2's real size depends on how claims concentrate across entities — a corpus where a few entities carry many claims produces far more pairs than a uniform one. Measure and report what the corpus actually yields. Never tune the data to hit a number from this document; a 1,000× reduction is as good a story as a 5,000× one, and an honest measured figure survives a judge's follow-up question.

Stage 3 runs in Python with no model call. Instrument all four numbers and surface them in `/stats` — they are the headline of the demo and the proof that FalkorDB is load-bearing.

**LLM response caching is mandatory, not an optimisation.** Hash the input (prompt + content + model), cache the response to disk under `/cache`, never pay for the same call twice. Extraction will be re-run many times while tuning prompts; without this you burn a day's free quota by Friday. Build the cache before the first real extraction run. `/cache` is gitignored.

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

The Adjudicator calls this **before** judging a pair. If precedent exists and the claims are unchanged, it does not re-flag. If a resolved conflict reappears with changed text, it escalates instead of duplicating.

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

---

## 8. MCP tool signatures

All tools return JSON. Errors return `{"error": "<message>"}` with HTTP 200 — the agent handles them, not the transport.

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

---

## 9. HTTP API

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
  -> {"correction": str, "owner": Person, "ticket": {"title","body"}}

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
}

type GraphPath = {
  nodes: { id: string; label: string; type: string; state?: "live"|"contradicted"|"superseded" }[]
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

`node.type` in `GraphPath` is the node label lowercased (`claim`, `document`, `decision`, `system`, `person`, `message`, `ticket`). B maps those to icons.

---

## 10. Fixtures — Dev B starts against these, today

Allen writes these before anything else. They are the real shapes, not sketches.

```
/fixtures/conflicts.json     GET /conflicts          (6 conflicts, all 3 kinds)
/fixtures/conflict-01.json   GET /conflicts/{id}     (with full GraphPath)
/fixtures/stats.json         GET /stats
/fixtures/mini-corpus.json   20 docs, for Allen's extraction before C's generator lands
```

B builds entirely against these until Friday night. **If the live API disagrees with a fixture, the API is wrong and Allen fixes it** — not the frontend. That rule is what makes integration 20 minutes instead of four hours.

---

## 11. Rules

1. FalkorDB is the only **database**. No Postgres, no vector DB, no second store of record. The `/cache` directory is not a database — it is memoised LLM responses on disk and is required by rule 7.
2. Raw Cypher, no ORM. Judges read our queries.
3. The UI never renders the full graph — only a traversal path, cap 40 nodes.
4. Extraction never runs on the default demo path. Graph is pre-built and shipped as an RDB dump.
5. Confidence floor 0.65. Nothing below it enters the graph.
6. `evidence_span` must be a literal substring of its source, always. Drop any claim where it is not.
7. Every LLM call is cached to disk by input hash. No exceptions — free-tier quota is the binding constraint.
8. `CONTRADICTS.method` records the model that judged the pair, e.g. `"gemini-2.0-flash"`. Provenance is what this product is about; our own edges should carry it too.
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