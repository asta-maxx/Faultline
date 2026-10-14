# Session notes — checkpoint 2026-10-15

Where Allen's track stands, what's verified, and how to pick up. Written against CONTRACT.md v4.

## Done and verified

| Area | Evidence |
| --- | --- |
| Repo skeleton, uv, Python 3.12 | `uv sync` |
| Schema (§5.3) | idempotent; all 7 unique constraints OPERATIONAL; duplicate `Claim.id` rejected |
| Queries §7.1–§7.5 (v4) | `python -m graph.collapse_demo` → ALL CHECKS PASSED |
| Stage 3 prefilter | matches brute-force oracle at floors 0.65 and 0.80 |
| LLM providers + disk cache | live Groq and Gemini calls; repeats served from `/cache` |
| Retry/backoff | 429 waits on provider retry delay ≤ 20 s, else overflow; 5xx/timeouts back off |
| Fixtures (v3/v4 shapes) | strict shape check passes; `stats.json` values are placeholders (see `fixtures/README.md`) |
| README + themed SVGs | `python .github/readme/build.py` |

## In progress

**Surveyor** (`agent/surveyor.py`, evaluated by `agent/survey_eval.py`), written directly, **not via Graphiti**, so no embeddings are needed.

- Phase 1 (per-source extraction on Groq, 12 workers) has completed once and is cached.
- Phase 2 (entity resolution) failed first with Groq `json_validate_failed`. It now uses `reasoning_effort: low`, `max_completion_tokens: 8192` and a compact output shape. The re-run was in flight at checkpoint time.
- Not yet reported: claim drop rate and reasons, entity count, near-duplicates, measured funnel on the corpus, planted-contradiction survival (out of 7).

Resume with:

```bash
set -a; . "./.env copy.example"; set +a      # until the key file is renamed to .env
export FALKOR_URL=redis://localhost:6380
uv run python -m agent.survey_eval            # extraction is cached, only new calls go live
```

Output graph: `faultline:minicorpus`. It is deliberately not `faultline:northwind`, which Dev C's ingest owns.

## Findings to act on

1. **Gemini free tier is the binding constraint, not latency.** Clean samples: min 1.76 s, median 2.96 s, max 6.38 s (the 22 s was an outlier). But in about 30 requests we hit a 503 (high demand), a 60 s+ timeout, a per-minute 429, and then the **daily quota** (retry after ~3 h 16 min). Roughly 100 judging calls a day on one key won't fit on `gemini-3.5-flash` free tier.
2. **CONTRACT §2 still lists "Extraction | Graphiti onto FalkorDB".** Extraction is written directly; that row needs updating.
3. **Keys live in `.env copy.example`.** Rename it to `.env`. All `.env*` files except `.env.example` are gitignored.

## Local environment

- FalkorDB runs in the `faultline-falkordb` container on **port 6380**, because 6379 is held by another project's `fusecode-redis`, which we don't touch.
- Test graphs: `faultline:synthetic` (collapse demo) and `faultline:minicorpus` (Surveyor).
