# Fixtures

Mock API responses in the exact shapes of CONTRACT §9. The live API is the default; start it with `FAULTLINE_FIXTURES=1` to serve these files instead, for frontend work without a graph. Only three endpoints are served in that mode: `GET /api/stats`, `GET /api/conflicts` and `GET /api/conflicts/{id}` (only `conflict-01` has a detail file; any other id is a 404). If the live API disagrees with a fixture, the API is wrong.

The fixtures carry none of the optional v5 and v7 fields (`judgement`, `resolution`, `precedent`).

| File | Endpoint | Notes |
| --- | --- | --- |
| `conflicts.json` | `GET /conflicts` | 6 open conflicts covering all three kinds, ranked by `blast_radius` (max of the two sides, §7.3) |
| `conflict-01.json` | `GET /conflicts/{id}` | the superseded cold-chain case with its full 14-node `GraphPath` |
| `stats.json` | `GET /stats` | **values are placeholders**, see below |
| `mini-corpus.json` | none | 20 documents, 3 messages and 1 ticket for extraction, with an answer key of 7 planted contradictions |

## `stats.json` values are placeholders

The numbers in `stats.json`, and the copy embedded in `conflicts.json`, are **not measured**. They sit inside the orders of magnitude in CONTRACT §6 so the UI has realistic widths to lay out: about 10⁶ naive pairs, 10³ collapsed, 10² prefiltered and 10² judged. They replace nothing and prove nothing. They remain placeholders: the measured Northwind numbers (57,291 → 1,666 → 202 → 159 judged → 20 conflicts) come from the live `GET /api/stats`, not from this file.

JSON has no comments, and a `_comment` key would break the exact `Stats` shape, so this note lives here instead.

Don't use the synthetic test graph's funnel (`graph/collapse_demo.py`) as stand-in data. That graph has 40 claims and is shaped to exercise edge cases, not to resemble a real corpus.
