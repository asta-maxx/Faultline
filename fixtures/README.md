# Fixtures

Mock API responses in the exact shapes of CONTRACT §9. The frontend builds against these until the live API lands. If the live API disagrees with a fixture, the API is wrong.

| File | Endpoint | Notes |
| --- | --- | --- |
| `conflicts.json` | `GET /conflicts` | 6 open conflicts covering all three kinds, ranked by `blast_radius` (max of the two sides, §7.3) |
| `conflict-01.json` | `GET /conflicts/{id}` | the superseded cold-chain case with its full 14-node `GraphPath` |
| `stats.json` | `GET /stats` | **values are placeholders**, see below |
| `mini-corpus.json` | none | 20 documents, 3 messages and 1 ticket for extraction, with an answer key of 7 planted contradictions |

## `stats.json` values are placeholders

The numbers in `stats.json`, and the copy embedded in `conflicts.json`, are **not measured**. They sit inside the orders of magnitude in CONTRACT §6 so the UI has realistic widths to lay out: about 10⁶ naive pairs, 10³ collapsed, 10² prefiltered and 10² judged. They replace nothing and prove nothing. They are swapped for measured values once a real corpus has been ingested.

JSON has no comments, and a `_comment` key would break the exact `Stats` shape, so this note lives here instead.

Don't use the synthetic test graph's funnel (`graph/collapse_demo.py`) as stand-in data. That graph has 40 claims and is shaped to exercise edge cases, not to resemble a real corpus.
