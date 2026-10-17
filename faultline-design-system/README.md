# Faultline

**Your company disagrees with itself. Faultline finds where.**

Faultline is an agent that audits an organisation's documented knowledge for self-contradiction, ranks each conflict by what is downstream of it, and repairs it. Built for Graph Hacks 2026 (FalkorDB × WeMakeDevs), Track 03 Company Brain and Track 02 Agent Memory and Coordination.

This page is the visual identity. Build the UI from these tokens, not from screenshots.

---

## The idea the identity has to carry

A faultline is a fracture where two layers of rock that were once continuous have shifted out of alignment. You can read the displacement directly: the same stratum appears on both sides at different heights. That is exactly what the product finds — the same claim, asserted twice, no longer lining up.

So the identity is **archival, not AI-startup**. Faultline looks like a records system: a thing that keeps evidence, dates it, and shows its working. It does not look like a chat product.

**What we are not:** no purple-to-blue gradient, no emoji section markers, no rounded cards with a colored left rail, no centered hero. If a slide of ours could be swapped into another team's deck without anyone noticing, it is wrong.

---

## The mark

A block of four strata, cut by a vertical fault, the right side displaced down by exactly one band. One stratum is picked out in `state-live` on both sides, so the eye catches that it is the *same* layer at two heights. The fault itself is a hairline in `state-contradicted`.

Two versions ship: `faultline-mark-ink.svg` for light grounds, `faultline-mark-paper.svg` for dark. There is no gradient version and no icon-in-a-rounded-square version.

**Clear space** on all sides is the height of one band (11 units at the 64-unit viewBox, so ~17% of the mark's height). **Minimum size** 24px — below that the displacement stops reading and you should use the wordmark alone.

**Lockup:** mark left, wordmark right, separated by one band height. Wordmark is `Faultline` set in Spectral 500, sentence case, optical size matched so the cap height equals three bands. Never set the name in all caps, never letterspace it, never stack it under the mark.

**Never:** recolor the mark outside the palette, rotate it, remove the fault hairline, align the two halves, or place it on a photograph.

---

## Color

Dark is the product's default — it is a monitoring surface people leave open, and the evidence reads better on it. Light exists for the README, the blog post and print.

The palette is four neutrals and four states. **The four states are the whole semantic system** and they map one-to-one onto the graph:

| Token | Means | In the graph |
| --- | --- | --- |
| `state-live` | This is current | the claim the `SUPERSEDES` chain lands on |
| `state-contradicted` | This is in conflict | an endpoint of a `CONTRADICTS` edge |
| `state-superseded` | This was retired | a `Decision` with a successor |
| `state-resolved` | This was settled before | a `Conflict` with a `RESOLVED_AS` edge |

Neutrals are warm-biased, never pure grey — a neutral pulled slightly toward the ochre reads as chosen rather than inherited.

**Rules.** Never carry meaning in color alone: every state also has a glyph and a word, because a conflict badge that is only red fails for a colorblind judge watching a demo video. `state-superseded` and `rule` never set text. `state-live` is the only accent — if something needs to stand out and is not the current claim, it does not get color, it gets weight or space.

---

## Type

Three families, each with a job, and the split is the point:

- **Spectral** (serif) — display and headings. Serif reads as *record*, which is the whole positioning. Used with restraint: headings only, never body.
- **IBM Plex Sans** — all interface text and running copy. Technical without being the default grotesque everyone else will ship.
- **JetBrains Mono** — node IDs, Cypher, document paths, confidence scores, timestamps. Anything the system generated rather than a person wrote appears in mono. That rule is load-bearing: it is how a reader tells evidence from narration at a glance.

Running text stays near 65 characters. Labels are the only uppercase, at `label` with its letterspacing. Digits that line up in a column take `font-variant-numeric: tabular-nums`.

---

## The motif: the traversal path

One graphic carries the whole brand, and it is the same one everywhere: **the subgraph Faultline actually walked to reach an answer**, with superseded nodes faded beneath the live one rather than deleted — the record visibly written over.

It appears as the UI's main panel, the README hero, the blog header, the slide backgrounds and the demo thumbnail. Render only the path, capped around 40 nodes. Never render the whole graph: a hairball says "we have a lot of data", the path says "here is the proof".

---

## Voice

Archival and plain. State the finding, then the evidence, then the date.

> Decided 14 March by R. Menon. Superseded 2 August by ADR-88. 41 documents still cite it.

No exclamation marks. No "AI-powered", no "revolutionise", no rocket emoji. Errors say what broke and what to do. Confidence is always a number, never an adjective.

---

## Shape

Square by default. `radius-none` on panels, tables and the canvas; `radius-sm` only on chips and evidence spans. Rounded corners everywhere is the single clearest tell of a generated interface, and avoiding them costs nothing.

Hairlines over shadows. Depth comes from `surface-sunken` / `surface-base` / `surface-raised`, not from a drop shadow on every card.
