# Session notes: checkpoint 2026-10-17

Where the project stands and how to pick up. Written against CONTRACT.md v7. The README's [Status](README.md#status) table carries the detail; this page is the short version.

## Done and verified

| Area | Evidence |
| --- | --- |
| Schema, queries §7.1–§7.5, prefilter | `uv run --env-file .env python -m graph.collapse_demo` prints ALL CHECKS PASSED |
| LLM providers + disk cache | Groq extracts, Gemini judges with Groq overflow; every call cached under `cache/` |
| Surveyor on the Northwind demo slice | 100 sources, 339 claims, 79 entities |
| Adjudicator + blast radius | 20 open conflicts in `faultline:northwind` |
| Demo graph | `faultline:northwind`: 3,264 nodes, 1,567 edges (2,826 / 823 structural, plus claims, entities and conflicts) |
| HTTP API, CONTRACT §9 and §9b | live by default; `?workspace=<id>`; resolve and dismiss return 409 unless the conflict is open; `GET /api/conflicts/{id}` returns `precedent` |
| Workspaces and folder audits | `faultline:_registry`; an audit cut off by a restart is saved as failed |
| MCP tools | six §8 tools at `/mcp/`, each with an optional `workspace` argument |
| Docker image | builds the UI, generates the corpus (`corpus.json` SHA-256 `0d44f7db…`), cache at `/cache`, listens on `$PORT` |
| Tests | `uv run --env-file .env pytest -q`: 48 passed |

## Measured results

- Funnel: 57,291 → 1,666 → 202 → 159 judged → 20 conflicts.
- 16 of the 20 conflicts correspond to 13 of the 14 planted contradictions, 11 with the correct kind.
- 4 false positives: 3 from over-merged ticket "Incident" entities, 1 judge error.
- 12 planted contradictions reach stage 3 as the planted pair itself (claims from both planted source documents). 13 surface, because a conflict can pair one planted-source claim with a distractor document restating the other value. Both numbers are true.
- The planted set was also the development set, so these numbers are optimistic.

## In progress

- Web UI: DRAFT CORRECTION, ASSIGN (opens the drafted ticket for the owner; there is no assignment endpoint), RESOLVE, DISMISS and a precedent line are being wired in this branch.

## Open items

1. Demo video.
2. Deploy: no public URL yet. `infra/RAILWAY.md` is the runbook; restore the demo RDB, do not seed.
3. LICENSE: not chosen yet.
4. Plant 10: the one planted contradiction not surfaced.
5. The 4 false positives above.
6. Folder-audit limits: no `Person`, `System` or `Decision` nodes, so blast radius is the document count, conflicts have no owner, `/draft` returns 422, and the `superseded` kind cannot occur. Git sources are saved, not cloned.

## Local environment

- FalkorDB runs in the `faultline-falkordb` container on **port 6380**, because 6379 belongs to another project's Redis, which we don't touch. `.env` sets `FALKOR_URL=redis://localhost:6380`.
- Test graphs: `faultline:synthetic` (collapse demo), plus throwaway graphs created and deleted by the tests.
