"""Generates every README visual from the Faultline design system (faultline-design-system/).

    python .github/readme/build.py

Each diagram is written as <name>-light.svg and <name>-dark.svg; the README switches between
them with <picture> so they follow the reader's GitHub theme. Colours are the design tokens
(tokens.css), nothing else: four warm neutrals, ochre `live` as the only accent, and the four
state colours used only for the states they name. Square corners, hairlines, no shadows.

Type follows the system (Spectral headings, IBM Plex Sans text, JetBrains Mono for anything the
system generated). GitHub serves these SVGs as images, which cannot load web fonts, so each
family falls back to the nearest common face: Georgia, the platform sans, the platform mono.

The funnel numbers are MEASURED on faultline:northwind (GET /api/stats); update FUNNEL after
an audit. No emoji.
"""

from __future__ import annotations

import math
from pathlib import Path

OUT = Path(__file__).resolve().parent

# Measured on faultline:northwind (Northwind demo slice: 60 documents, 20 tickets, 20 messages).
FUNNEL = {"naive": 57291, "collapsed": 1666, "prefiltered": 202, "judged": 159, "conflicts": 20, "claims": 339}

# tokens.css, verbatim. live / contradicted / superseded / resolved are the whole semantic system.
THEMES = {
    "dark": dict(base="#0B0C0E", raised="#15171A", sunken="#060708", ink="#E8E3D9", muted="#9A948A",
                 rule="#262A2F", live="#C9873A", contra="#D4685C", super="#5A5F66", resolved="#6E8F6B",
                 mark_strata="#E8E3D9", mark_live="#C9873A", mark_fault="#B4544A"),
    "light": dict(base="#E8E3D9", raised="#F2EEE7", sunken="#DCD5C7", ink="#1A1714", muted="#5C564C",
                  rule="#CEC6B6", live="#8A5415", contra="#8E3B32", super="#9A9388", resolved="#3D5C3A",
                  mark_strata="#1A1714", mark_live="#A96B23", mark_fault="#8E3B32"),
}
# Section icons are single files on GitHub's own white or near-black page: the mark's light-ground ochre
# holds about 4:1 on both.
ICON = "#A96B23"

DISPLAY = "Spectral, 'Iowan Old Style', Georgia, serif"
SANS = "'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def tw(s: str, size: float, mono: bool = False, display: bool = False) -> float:
    """Rough text width; fallback fonts vary, so layouts leave slack."""
    return len(s) * size * (0.62 if mono else 0.5 if display else 0.55)


def text(x, y, s, size=16, fill="ink", t=None, weight=400, anchor="start", face="sans", ls=None, opacity=None):
    color = t[fill] if t and fill in t else fill
    family = {"sans": SANS, "mono": MONO, "display": DISPLAY}[face]
    extra = f' letter-spacing="{ls}"' if ls is not None else ""
    extra += f' opacity="{opacity}"' if opacity is not None else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}"{extra}>{esc(s)}</text>')


def label(x, y, s, t, fill="muted", anchor="start"):
    """The system's uppercase label: mono, tracked, the only uppercase text."""
    return text(x, y, s.upper(), 11, fill, t, 400, anchor, "mono", ls=1.2)


def frame(w, h, t, body, title, desc):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-labelledby="t d">\n<title id="t">{esc(title)}</title><desc id="d">{esc(desc)}</desc>\n'
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" fill="{t["base"]}" stroke="{t["rule"]}"/>\n'
            f'{body}\n</svg>\n')


def markers(t, keys):
    return "<defs>" + "".join(
        f'<marker id="ar-{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{t[k]}"/></marker>' for k in keys) + "</defs>"


def arrow(x1, y1, x2, y2, t, color="muted", dash=False, width=1.2):
    d = ' stroke-dasharray="6 4"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{t[color]}" '
            f'stroke-width="{width}"{d} marker-end="url(#ar-{color})"/>')


def edge_label(cx, cy, s, t, color="muted"):
    """An edge name on its line: mono on a plate of the ground colour, like the app's graph."""
    w = tw(s, 11, mono=True) + 10
    return (f'<rect x="{cx - w / 2:.1f}" y="{cy - 9:.1f}" width="{w:.1f}" height="18" fill="{t["base"]}"/>'
            + text(cx, cy + 4, s, 11, color, t, 400, "middle", "mono"))


def chip(x, y, s, t, color="muted", stroke="rule"):
    """Chips are the one place radius-sm (2px) is allowed."""
    w = tw(s.upper(), 11, mono=True) + 20
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="26" rx="2" fill="none" stroke="{t[stroke]}"/>'
            + text(x + w / 2, y + 17, s.upper(), 11, color, t, 400, "middle", "mono", ls=1.2)), w


def node(cx, cy, title, sub, t, w=200, h=72, stroke="rule", weight=600, sub2=None):
    out = (f'<rect x="{cx - w / 2:.1f}" y="{cy - h / 2:.1f}" width="{w}" height="{h}" fill="{t["raised"]}" '
           f'stroke="{t[stroke]}"/>' + text(cx, cy - (10 if sub2 else 2), title, 16, "ink", t, weight, "middle"))
    if sub:
        out += text(cx, cy + (12 if sub2 else 18), sub, 12, "muted", t, 400, "middle", "mono")
    if sub2:
        out += text(cx, cy + 29, sub2, 12, "muted", t, 400, "middle", "mono")
    return out


def mark(x, y, size, t):
    """The Faultline mark (faultline-mark-*.svg): four strata cut by a fault, the right side
    displaced down one band, the same stratum picked out in live on both sides."""
    s = size / 64
    rects = [(6, 8, "s"), (6, 19, "l"), (6, 30, "s"), (6, 41, "s"),
             (34, 19, "s"), (34, 30, "l"), (34, 41, "s"), (34, 52, "s")]
    out = "".join(f'<rect x="{x + rx * s:.2f}" y="{y + ry * s:.2f}" width="{24 * s:.2f}" height="{7 * s:.2f}" '
                  f'fill="{t["mark_live"] if k == "l" else t["mark_strata"]}"/>' for rx, ry, k in rects)
    return out + f'<rect x="{x + 31 * s:.2f}" y="{y + 4 * s:.2f}" width="{2 * s:.2f}" height="{57 * s:.2f}" fill="{t["mark_fault"]}"/>'


# State glyphs (rule 9: colour never carries meaning alone; every state has a shape and a word).
def glyph(kind, cx, cy, r, t):
    c = {"live": t["live"], "contradicted": t["contra"], "superseded": t["super"], "resolved": t["resolved"]}[kind]
    k = r * 0.45
    if kind == "resolved":  # settled: a check in a square, the record closed
        ring = f'<rect x="{cx - r:.1f}" y="{cy - r:.1f}" width="{2 * r:.1f}" height="{2 * r:.1f}" fill="none" stroke="{c}" stroke-width="1.6"/>'
    else:
        ring = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c}" stroke-width="1.6"/>'
    if kind in ("live", "resolved"):
        mark_ = f'<path d="M{cx - k:.1f} {cy:.1f}l{k * 0.7:.1f} {k * 0.75:.1f}l{k * 1.35:.1f} -{k * 1.5:.1f}"'
    elif kind == "contradicted":
        mark_ = f'<path d="M{cx - k:.1f} {cy - k:.1f}L{cx + k:.1f} {cy + k:.1f}M{cx + k:.1f} {cy - k:.1f}L{cx - k:.1f} {cy + k:.1f}"'
    else:  # superseded: double chevron, "replaced by something newer"
        mark_ = (f'<path d="M{cx - k:.1f} {cy - k * 0.8:.1f}l{k * 0.8:.1f} {k * 0.8:.1f}l-{k * 0.8:.1f} {k * 0.8:.1f}'
                 f'M{cx:.1f} {cy - k * 0.8:.1f}l{k * 0.8:.1f} {k * 0.8:.1f}l-{k * 0.8:.1f} {k * 0.8:.1f}"')
    return ring + mark_ + f' fill="none" stroke="{c}" stroke-width="1.6" stroke-linecap="square" stroke-linejoin="miter"/>'


def sq(cx, cy, t, stroke="rule", size=34, opacity=None):
    """A graph node as the app draws it: a square, 1px border."""
    o = f' opacity="{opacity}"' if opacity is not None else ""
    return (f'<rect x="{cx - size / 2:.1f}" y="{cy - size / 2:.1f}" width="{size}" height="{size}" '
            f'fill="{t["raised"]}" stroke="{t[stroke]}"{o}/>')


# ---------------------------------------------------------------- hero
def hero(t):
    w, h = 1200, 380
    b = [markers(t, ["muted", "contra"])]
    # lockup: mark left, wordmark right, one band apart; cap height three bands
    b.append(mark(64, 64, 72, t))
    b.append(text(158, 122, "Faultline", 60, "ink", t, 500, face="display"))
    b.append(text(66, 196, "Your company disagrees with itself.", 30, "ink", t, 500, face="display"))
    b.append(text(66, 236, "Faultline finds where.", 30, "ink", t, 500, face="display"))
    b.append(text(66, 278, "It ranks every contradiction by what sits downstream of it,", 16, "muted", t))
    b.append(text(66, 302, "shows the traversal path that proves it, and routes it to the owner.", 16, "muted", t))
    x = 66
    for s in ("Graph Hacks 2026", "FalkorDB × WeMakeDevs", "Track 03 Company Brain", "Track 02 Agent Memory"):
        c, cw = chip(x, 326, s, t)
        b.append(c)
        x += cw + 8

    # the motif: the path Faultline walked, the record visibly written over
    gx = 760
    b.append(label(gx, 52, "the path behind one answer", t))
    b.append(f'<line x1="{gx}" y1="66" x2="1150" y2="66" stroke="{t["rule"]}"/>')
    rows = {"2026-09": 120, "2026-03": 210, "2024-06": 300}
    for month, y in rows.items():
        b.append(text(gx, y + 4, month, 11, "muted", t, 400, face="mono"))
        b.append(f'<line x1="{gx}" y1="{y + 44}" x2="1150" y2="{y + 44}" stroke="{t["rule"]}" stroke-dasharray="3 4"/>')
    pts = {"run": (870, 120), "c30": (990, 120), "pol": (870, 210), "c15": (990, 210),
           "adr88": (1100, 210), "adr41": (1100, 300)}
    lines = [("run", "c30", "ASSERTS", "muted"), ("pol", "c15", "ASSERTS", "muted"),
             ("pol", "adr88", None, "muted"), ("adr88", "adr41", "SUPERSEDES", "muted")]
    for a, c, name, col in lines:
        (x1, y1), (x2, y2) = pts[a], pts[c]
        ex, ey = (x2 - 20, y2) if y1 == y2 else (x2, y2 - 20)
        b.append(arrow(x1 + 18, y1, ex, ey, t, col) if y1 == y2 else arrow(x1, y1 + 18, ex, ey, t, col))
        if name:
            b.append(edge_label((x1 + x2) / 2, (y1 + y2) / 2, name, t))
    # pol -> adr88 is a CITES edge drawn along the row
    b.append(edge_label(1045, 210, "CITES", t))
    (x1, y1), (x2, y2) = pts["c30"], pts["c15"]
    b.append(arrow(x1, y1 + 18, x2, y2 - 20, t, "contra", dash=True, width=1.4))
    b.append(edge_label(x1, (y1 + y2) / 2, "CONTRADICTS", t, "contra"))
    b.append(sq(*pts["run"], t))
    b.append(sq(*pts["pol"], t))
    b.append(sq(*pts["c30"], t, "contra"))
    b.append(sq(*pts["c15"], t, "live"))
    b.append(sq(*pts["adr88"], t, "live"))
    b.append(sq(*pts["adr41"], t, "super", opacity=0.45))
    names = {"run": "runbook", "pol": "policy v3", "c30": "30 min", "c15": "15 min", "adr88": "ADR-88", "adr41": "ADR-41"}
    for k, (px, py) in pts.items():
        b.append(text(px, py + 34, names[k], 11, "ink" if k != "adr41" else "muted", t, 400, "middle", "mono",
                      opacity=0.45 if k == "adr41" else None))
    return frame(w, h, t, "\n".join(b), "Faultline",
                 "The Faultline mark and wordmark: your company disagrees with itself, Faultline finds where. Beside it, "
                 "the path behind one answer: a runbook asserts 30 minutes, a policy asserts 15 minutes and cites ADR-88, "
                 "which supersedes ADR-41; the two claims are joined by a CONTRADICTS edge.")


# ---------------------------------------------------------------- stack strip
def stack(t):
    items = ["Python 3.12", "FastAPI", "FalkorDB · raw Cypher", "Gemini free tier", "Groq overflow",
             "Vite + React + TS", "Cytoscape.js", "$0 budget"]
    widths = [tw(s.upper(), 11, mono=True) + 20 for s in items]
    gap = 8
    total = sum(widths) + gap * (len(items) - 1)
    w, h = max(1200, int(total + 48)), 64
    x, b = (w - total) / 2, []
    for s in items:
        c, cw = chip(x, 19, s, t, "ink")
        b.append(c)
        x += cw + gap
    return frame(w, h, t, "\n".join(b), "Stack", "Python 3.12, FastAPI, FalkorDB with raw Cypher, Gemini free tier, "
                 "Groq overflow, Vite React TypeScript, Cytoscape.js, zero budget.")


# ---------------------------------------------------------------- funnel
def funnel(t):
    w, h = 1200, 640
    f = FUNNEL
    rows = [("Stage 1", "All possible pairs", "n·(n−1)/2 · counted, never enumerated", f["naive"]),
            ("Stage 2", "Graph collapse", "shared Entity · Cypher §7.1", f["collapsed"]),
            ("Stage 3", "Deterministic prefilter", "same predicate · object or polarity differs", f["prefiltered"]),
            ("Stage 4", "LLM judgement", "one cached call per disagreement", f["judged"]),
            ("Result", "Contradictions", "CONTRADICTS edge + open Conflict", f["conflicts"])]
    bx, maxw = 560, 560
    top = math.log10(f["naive"])
    b = []
    for i, (stage, name, mech, n) in enumerate(rows):
        y = 40 + i * 112
        b.append(f'<line x1="40" y1="{y + 96}" x2="{w - 40}" y2="{y + 96}" stroke="{t["rule"]}"/>')
        b.append(label(56, y + 22, stage, t, "live" if i == 4 else "muted"))
        b.append(text(56, y + 52, name, 21, "ink", t, 500, face="display"))
        b.append(text(56, y + 76, mech, 13, "muted", t, 400, face="mono"))
        b.append(text(bx - 24, y + 62, f"{n:,}", 34, "live" if i == 4 else "ink", t, 400, "end", "mono"))
        bw = max(6.0, maxw * math.log10(max(n, 1)) / top)
        b.append(f'<rect x="{bx}" y="{y + 44}" width="{maxw}" height="2" fill="{t["rule"]}"/>'
                 f'<rect x="{bx}" y="{y + 42}" width="{bw:.1f}" height="6" fill="{t["live"] if i == 4 else t["ink"]}"/>')
    b.append(text(56, h - 22, f"Measured on faultline:northwind ({f['claims']} claims from 100 sources). Bars are log-scaled; "
                  f"{f['naive'] / f['prefiltered']:.0f}× fewer pairs reach the model.", 13, "muted", t, 400, face="mono"))
    return frame(w, h, t, "\n".join(b), "The funnel",
                 f"Measured on faultline:northwind: {f['naive']:,} possible pairs, {f['collapsed']:,} after the graph "
                 f"collapse, {f['prefiltered']} after the deterministic prefilter, {f['judged']} judged by the model, "
                 f"{f['conflicts']} contradictions.")


# ---------------------------------------------------------------- architecture
def architecture(t):
    w, h = 1200, 470
    b = [markers(t, ["muted", "contra"])]
    top, bot = 150, 360
    b.append(label(60, 54, "ingest and serve", t))
    b.append(label(60, 290, "the funnel", t))
    for i, s in enumerate(["Documents", "Messages", "Tickets"]):
        y = top - 44 + i * 44
        b.append(f'<rect x="40" y="{y - 17}" width="150" height="34" fill="{t["raised"]}" stroke="{t["rule"]}"/>'
                 + text(115, y + 5, s, 14, "ink", t, 400, "middle"))
    b.append(arrow(194, top, 262, top, t))
    b.append(node(370, top, "Surveyor", "claim extraction", t, sub2="Groq · cached"))
    b.append(arrow(474, top, 536, top, t))
    # FalkorDB: the load-bearing store gets weight, not colour
    b.append(f'<rect x="542" y="{top - 52}" width="196" height="104" fill="{t["raised"]}" stroke="{t["ink"]}" stroke-width="1.6"/>'
             + text(640, top - 4, "FalkorDB", 20, "ink", t, 500, "middle", "display")
             + text(640, top + 20, "faultline:{workspace}", 12, "muted", t, 400, "middle", "mono")
             + text(640, top + 38, "one graph each", 12, "muted", t, 400, "middle", "mono"))
    b.append(arrow(744, top, 806, top, t))
    b.append(node(910, top, "FastAPI + MCP", "one process", t, sub2="HTTP §9 · tools §8"))
    b.append(arrow(1012, top, 1046, top, t))
    b.append(f'<rect x="1050" y="{top - 52}" width="112" height="104" fill="{t["raised"]}" stroke="{t["rule"]}"/>'
             + text(1106, top - 6, "Web UI", 16, "ink", t, 600, "middle") + text(1106, top + 16, "ranked queue", 11, "muted", t, 400, "middle", "mono")
             + text(1106, top + 32, "path ≤ 40", 11, "muted", t, 400, "middle", "mono"))
    b.append(arrow(600, top + 56, 470, bot - 50, t))
    b.append(node(400, bot, "Collapse", "stage 2 · Cypher §7.1", t, 210, 96, sub2="shared Entity only"))
    b.append(arrow(507, bot, 571, bot, t))
    b.append(node(680, bot, "Prefilter", "stage 3 · Python", t, 210, 96, sub2="no model call"))
    b.append(arrow(787, bot, 851, bot, t))
    b.append(node(960, bot, "Adjudicator", "stage 4 · LLM judge", t, 210, 96, sub2="precedent first §7.4"))
    b.append(arrow(905, bot - 50, 700, top + 58, t, "contra"))
    b.append(edge_label(830, 268, "writes CONTRADICTS · Conflict", t, "contra"))
    return frame(w, h, t, "\n".join(b), "Architecture",
                 "Documents, messages and tickets flow into the Surveyor, which extracts claims into FalkorDB, one graph per "
                 "workspace. The funnel reads from FalkorDB: graph collapse, deterministic prefilter, then the Adjudicator, "
                 "which writes CONTRADICTS edges and Conflicts back. FastAPI and MCP serve the ranked queue to the web UI.")


# ---------------------------------------------------------------- graph model
def graph_model(t):
    w, h = 1200, 680
    W, H = 184, 72
    N = {"Person": (112, 340, "name · role · active"),
         "Document": (380, 340, "title · path · kind"),
         "Claim": (680, 340, "predicate · object · polarity"),
         "Entity": (1000, 340, "one per real subject"),
         "Decision": (380, 120, "ref · status"),
         "Message": (680, 120, "channel · text"),
         "Ticket": (1000, 120, "ref · title · text"),
         "System": (380, 562, "tier 1–3"),
         "Conflict": (680, 562, "kind · status · blast_radius")}
    b = [markers(t, ["muted", "contra"])]

    def edge(x1, y1, x2, y2, name, lx, ly, color="muted"):
        return arrow(x1, y1, x2, y2, t, color) + edge_label(lx, ly, name, t, color)

    L, R, T, B = (lambda k: N[k][0] - W / 2), (lambda k: N[k][0] + W / 2), (lambda k: N[k][1] - H / 2), (lambda k: N[k][1] + H / 2)
    b.append(edge(R("Document"), 340, L("Claim") - 2, 340, "ASSERTS", 530, 340))
    b.append(edge(R("Claim"), 340, L("Entity") - 2, 340, "ABOUT", 840, 340))
    b.append(edge(640, B("Message"), 640, T("Claim") - 2, "ASSERTS", 640, 262))
    b.append(edge(720, T("Claim"), 720, B("Message") + 2, "DERIVED_FROM", 720, 200))
    b.append(edge(920, B("Ticket"), 742, T("Claim") - 2, "ASSERTS", 866, 200))
    b.append(edge(R("Claim"), T("Claim") + 18, 968, B("Ticket") + 2, "DERIVED_FROM", 822, 280))
    b.append(edge(380, T("Document"), 380, B("Decision") + 2, "CITES", 420, 230))
    b.append(edge(380, B("Document"), 380, T("System") - 2, "GOVERNS", 430, 451))
    b.append(edge(R("Person"), 340, L("Document") - 2, 340, "AUTHORED", 246, 316))
    b.append(edge(150, T("Person"), L("Decision") + 10, B("Decision") + 2, "AUTHORED", 196, 214))
    b.append(edge(150, B("Person"), L("System") - 2, 562, "OWNS", 198, 486))
    b.append(edge(660, T("Conflict"), 660, B("Claim") + 2, "INVOLVES", 604, 451))
    b.append(edge(700, T("Conflict"), 700, B("Claim") + 2, "RESOLVED_AS", 778, 451))
    dx, dy = L("Decision"), 120
    b.append(f'<path d="M{dx} {dy - 14} C{dx - 70} {dy - 50}, {dx - 70} {dy + 50}, {dx - 2} {dy + 14}" fill="none" '
             f'stroke="{t["muted"]}" stroke-width="1.2" marker-end="url(#ar-muted)"/>' + edge_label(dx - 30, dy - 52, "SUPERSEDES", t))
    cx_, cy_ = R("Claim"), B("Claim")
    b.append(f'<path d="M{cx_ - 30} {cy_} C{cx_ - 20} {cy_ + 70}, {cx_ + 70} {cy_ + 40}, {cx_ + 2} {cy_ - 12}" fill="none" '
             f'stroke="{t["contra"]}" stroke-width="1.4" stroke-dasharray="6 4" marker-end="url(#ar-contra)"/>'
             + edge_label(cx_ + 74, cy_ + 46, "CONTRADICTS", t, "contra"))
    for name, (x, y, props) in N.items():
        b.append(f'<rect x="{x - W / 2}" y="{y - H / 2}" width="{W}" height="{H}" fill="{t["raised"]}" stroke="{t["rule"]}"/>'
                 + text(x, y - 3, name, 17, "ink", t, 500, "middle", "display")
                 + text(x, y + 20, props, 11, "muted", t, 400, "middle", "mono"))
    lx, ly = 902, 528
    b.append(f'<rect x="{lx}" y="{ly}" width="248" height="104" fill="{t["sunken"]}" stroke="{t["rule"]}"/>'
             + text(lx + 16, ly + 26, "9 labels · 11 edge types", 14, "ink", t, 600)
             + text(lx + 16, ly + 50, "arrows point From → To", 12, "muted", t, 400, face="mono")
             + text(lx + 16, ly + 72, "one graph per workspace:", 12, "muted", t, 400, face="mono")
             + text(lx + 16, ly + 92, "faultline:{workspace_id}", 12, "live", t, 400, face="mono"))
    return frame(w, h, t, "\n".join(b), "Graph model",
                 "Nine node labels and eleven edge types. Documents, messages and tickets ASSERT claims; claims are ABOUT exactly "
                 "one Entity; claims CONTRADICT claims; Conflicts INVOLVE and RESOLVE_AS claims; documents CITE decisions and "
                 "GOVERN systems; decisions SUPERSEDE decisions; people AUTHOR documents and decisions and OWN systems.")


# ---------------------------------------------------------------- supersedes
def supersedes(t):
    w, h = 1200, 500
    b = [markers(t, ["muted"])]
    docs = [(250, "Cold Chain Excursion Runbook", "updated 2026-09-29 · newer", "reject after 30 min above 8 °C", "superseded"),
            (950, "Cold Chain Policy v3", "updated 2026-03-09 · older", "reject after 15 min above 8 °C", "live")]
    for x, title, upd, claim, state in docs:
        b.append(f'<rect x="{x - 210}" y="40" width="420" height="124" fill="{t["raised"]}" stroke="{t["rule"]}"/>'
                 + text(x - 186, 76, title, 18, "ink", t, 500, face="display") + text(x - 186, 100, upd, 12, "muted", t, 400, face="mono"))
        b.append(glyph(state, x - 172, 134, 10, t) + text(x - 152, 139, claim, 14, "ink", t, 400))
    adrs = [(250, "ADR-41", "superseded", "30 min, all loads"), (600, "ADR-63", "superseded", "20 min pharma"),
            (950, "ADR-88", "live", "15 min, all loads")]
    for x, ref, state, gist in adrs:
        faded = ' opacity="0.55"' if state == "superseded" else ""
        b.append(f'<g{faded}><rect x="{x - 120}" y="236" width="240" height="78" fill="{t["raised"]}" '
                 f'stroke="{t["live"] if state == "live" else t["super"]}"/>'
                 + glyph(state, x - 92, 275, 10, t) + text(x - 70, 271, ref, 17, "ink", t, 400, face="mono")
                 + text(x - 70, 294, f"{state} · {gist}", 12, "muted", t, 400, face="mono") + "</g>")
    b.append(arrow(830, 275, 722, 275, t) + edge_label(776, 256, "SUPERSEDES", t))
    b.append(arrow(480, 275, 372, 275, t) + edge_label(426, 256, "SUPERSEDES", t))
    b.append(arrow(250, 166, 250, 232, t, dash=True) + edge_label(250, 200, "CITES", t))
    b.append(arrow(950, 166, 950, 232, t, dash=True) + edge_label(950, 200, "CITES", t))
    rows = [("contradicted", "Timestamp logic", "the newest document wins → runbook → 30 min", "wrong"),
            ("live", "Traversal §7.2", "walk SUPERSEDES to the decision nothing supersedes → ADR-88 → 15 min", "right")]
    for i, (kind, head, body, verdict) in enumerate(rows):
        y = 356 + i * 62
        b.append(f'<rect x="40" y="{y}" width="1120" height="50" fill="{t["sunken"]}" stroke="{t["rule"]}"/>'
                 + glyph(kind, 70, y + 25, 11, t) + text(94, y + 31, head, 15, "ink", t, 600)
                 + text(260, y + 31, body, 13, "muted", t, 400, face="mono")
                 + label(1136, y + 30, verdict, t, "live" if kind == "live" else "contra", "end"))
    return frame(w, h, t, "\n".join(b), "Adjudication by traversal, not timestamp",
                 "The runbook was updated more recently but cites ADR-41, which ADR-63 and then ADR-88 supersede. "
                 "Timestamp logic picks the runbook's 30 minutes, which is wrong. Walking SUPERSEDES picks ADR-88's 15 minutes.")


# ---------------------------------------------------------------- states legend
def states(t):
    w, h = 1200, 96
    b = []
    items = [("live", "Live", "this is current"), ("contradicted", "Contradicted", "in an open conflict"),
             ("superseded", "Superseded", "a newer decision replaced it"), ("resolved", "Resolved", "settled before")]
    for i, (k, word, gloss) in enumerate(items):
        x = 48 + i * 284
        b.append(glyph(k, x + 14, 48, 12, t) + text(x + 38, 46, word, 17, "ink", t, 600)
                 + text(x + 38, 67, gloss, 12, "muted", t, 400, face="mono"))
    return frame(w, h, t, "\n".join(b), "Claim states",
                 "Live: a check in a circle. Contradicted: a cross in a circle. Superseded: a double chevron in a circle. "
                 "Resolved: a check in a square.")


# ---------------------------------------------------------------- icons (single file each, the app's stroke)
ICONS = {
    "funnel": '<path d="M3 4h18l-7 8.5V19l-4 2v-8.5z"/>',
    "flow": '<rect x="2.5" y="4" width="6" height="6"/><rect x="15.5" y="4" width="6" height="6"/>'
            '<rect x="9" y="15" width="6" height="6"/><path d="M8.5 7h7M18.5 10v3l-3.5 3M5.5 10v3l3.5 3"/>',
    "graph": '<rect x="2.5" y="3.5" width="5" height="5"/><rect x="16.5" y="3.5" width="5" height="5"/>'
             '<rect x="9.5" y="15.5" width="5" height="5"/><path d="M7.5 6h9M6.3 8.5l4.4 7M17.7 8.5l-4.4 7"/>',
    "query": '<path d="M8 6l-5.5 6L8 18M16 6l5.5 6L16 18M13.5 4l-3 16"/>',
    "gauge": '<path d="M3.5 17a8.5 8.5 0 1 1 17 0"/><path d="M12 17l4.5-6"/><circle cx="12" cy="17" r="1.6"/>',
    "states": '<circle cx="12" cy="12" r="9"/><path d="M8 12.3l2.7 2.7L16.5 9"/>',
    "terminal": '<rect x="2.5" y="4" width="19" height="16"/><path d="M6.5 9.5l3 2.5-3 2.5M12 15h5"/>',
    "key": '<circle cx="8" cy="15" r="4.5"/><path d="M11.2 11.8L20 3M16.5 6.5l2.5 2.5M14 9l2 2"/>',
    "tree": '<path d="M4 3v15a2 2 0 0 0 2 2h4M4 9h6M4 15h6"/><rect x="11" y="6.5" width="9" height="5"/>'
            '<rect x="11" y="12.5" width="9" height="5"/><rect x="11" y="18.5" width="9" height="3"/>',
    "status": '<path d="M9 6h11M9 12h11M9 18h11"/><path d="M3 6l1.5 1.5L7 5M3 12l1.5 1.5L7 11"/><circle cx="4.8" cy="18" r="1.6"/>',
    "shield": '<path d="M12 2.5l8 3v6c0 5-3.4 8.6-8 10-4.6-1.4-8-5-8-10v-6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    "chain": '<rect x="2.5" y="9" width="5.5" height="6"/><rect x="9.25" y="9" width="5.5" height="6"/>'
             '<rect x="16" y="9" width="5.5" height="6"/><path d="M5.25 9V6h13.5v3"/>',
}


def icon(body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
            f'stroke="{ICON}" stroke-width="1.75" stroke-linecap="square" stroke-linejoin="miter" aria-hidden="true">{body}</svg>\n')


def main():
    for name, fn in [("hero", hero), ("stack", stack), ("funnel", funnel), ("architecture", architecture),
                     ("graph-model", graph_model), ("supersedes", supersedes), ("states", states)]:
        for theme, t in THEMES.items():
            (OUT / f"{name}-{theme}.svg").write_text(fn(t), encoding="utf-8", newline="\n")
    for name, body in ICONS.items():
        (OUT / f"icon-{name}.svg").write_text(icon(body), encoding="utf-8", newline="\n")
    # The marks themselves, for anyone linking the logo (copied from faultline-design-system/assets/Logos).
    for theme, t in THEMES.items():
        (OUT / f"mark-{theme}.svg").write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" role="img" '
            f'aria-label="Faultline mark"><title>Faultline mark</title>{mark(0, 0, 64, t)}</svg>\n', encoding="utf-8", newline="\n")
    print(f"wrote {len(list(OUT.glob('*.svg')))} svgs to {OUT}")


if __name__ == "__main__":
    main()
