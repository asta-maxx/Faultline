# Session notes: checkpoint 2026-10-15

Where Allen's track stands, what's verified, and how to pick up. Written against CONTRACT.md v4.

## Done and verified

| Area | Evidence |
| --- | --- |
| Repo skeleton, uv, Python 3.12 | `uv sync` |
| Schema (§5.3) | idempotent; all 7 unique constraints OPERATIONAL; duplicate `Claim.id` rejected |
| Queries §7.1–§7.5 (v4) | `python -m graph.collapse_demo` prints ALL CHECKS PASSED |
| Stage 3 prefilter | matches a brute-force oracle at floors 0.65 and 0.80 |
| LLM providers + disk cache | live Groq and Gemini calls; repeats served from `/cache` |
| Retry/backoff | a 429 waits for the provider's retry delay up to 65 s, otherwise switches to the overflow model; 5xx and timeouts back off |
| Fixtures (v4 shapes) | strict shape check passes; `stats.json` values are placeholders (see `fixtures/README.md`) |
| README + themed SVGs | `python .github/readme/build.py` |

## Surveyor: in progress, not yet passing

`agent/surveyor.py`, evaluated by `agent/survey_eval.py`. It is written directly, **not via Graphiti**, so no embeddings are needed. Output goes to graph `faultline:minicorpus`, deliberately not `faultline:northwind`, which Dev C's ingest owns.

### Run 1: measured, and failed

| | |
| --- | --- |
| Sources | 24 (20 docs, 3 messages, 1 ticket); 3 failed with Groq JSON errors (doc-0127, doc-0162, doc-0193) |
| Claims | 127 raw, 123 kept, 4 dropped (3%), all `span_not_literal` |
| Entities | 83 from 83 subject refs: **resolution merged nothing** (the model returned an identity map) |
| Funnel | 7,503 → 84 → 4 → ≤ 4 |
| Planted contradictions | **0 of 7** reach stage 3: six split across different entities, one side of plant-7 not extracted |

### Fixes written since: not yet run

1. **Claim-level entity resolution.** Each claim, not each subject name, is assigned to a canonical entity, at the granularity a contradiction would be about. Its `subject_ref` becomes that entity's id, so §5's one-Entity-per-subject still holds. The prompt leans towards merging: over-merging costs stage-2 pairs, under-merging hides contradictions.
2. **Batched against a running catalogue.** 30 claims per call, each call shown the entities created so far. A single global call can't fit: **Groq's free tier caps `gpt-oss-120b` at 8,000 tokens per minute, and one request counts its completion budget too** (the global call asked for 8,105).
3. **JSON-failure retry.** A source whose JSON fails validation is retried once with `reasoning_effort: low` and a bounded completion budget.
4. **Waits up to 65 s.** Per-minute rate limits are waited out rather than switching to the overflow model, which would mix two models' outputs in one run.
5. **Resolver report.** The evaluator prints how many claims were re-assigned and how many the resolver left unassigned, so another silent no-op would show.

### Resume

```bash
uv run python -m agent.survey_eval     # .env supplies keys and FALKOR_URL; extraction calls are cached
```

Still to report: claim drop rate with reasons, entity count, near-duplicate entities, the measured funnel on the corpus, and how many of the 7 planted contradictions survive to stage 3. Each iteration tunes prompts against the same 20 documents, so treat the survival count as optimistic until a held-out corpus exists.

## Findings to act on

1. **The binding constraint is free-tier quota, not latency.**
   - Gemini `gemini-3.5-flash`: min 1.76 s, median 2.96 s, max 6.38 s over 8 clean calls. Within about 30 requests it also returned a 503 (high demand), a 60 s+ timeout, a per-minute 429, then the daily-quota 429 (~3 h 16 min until reset).
   - Groq `gpt-oss-120b`: 8,000 tokens per minute, so extracting an 1,800-claim corpus is minutes-to-hours of wall time, not seconds.
2. **CONTRACT §2 still lists "Extraction | Graphiti onto FalkorDB".** Extraction is written directly; that row needs updating.

## Local environment

- FalkorDB runs in the `faultline-falkordb` container on **port 6380**, because 6379 belongs to another project's `fusecode-redis`, which we don't touch. `.env` sets `FALKOR_URL=redis://localhost:6380`.
- Test graphs: `faultline:synthetic` (collapse demo) and `faultline:minicorpus` (Surveyor).
