"""Generates every README visual in two themes: Strata Light and Strata Dark.

    python .github/readme/build.py

Each diagram is written as <name>-light.svg and <name>-dark.svg; the README switches
between them with <picture> so they follow the reader's GitHub theme. Section icons are
single files in the fault accent, which holds 3:1 contrast on both GitHub backgrounds.
No emoji, no web fonts (GitHub serves SVGs as images, so only system fonts render).

The funnel numbers are MEASURED: update FUNNEL from `python -m graph.collapse_demo`.
"""

from __future__ import annotations

import math
from pathlib import Path

OUT = Path(__file__).resolve().parent

# Measured on faultline:synthetic (40 claims, 12 entities) by graph/collapse_demo.py.
FUNNEL = {"naive": 780, "collapsed": 56, "prefiltered": 12, "judged_max": 12, "claims": 40, "entities": 12}

THEMES = {
    "light": dict(  # Strata Light
        bg="#FBFAF7", card="#FFFFFF", line="#E3DFD6", grid="#ECE8E0", ink="#1A1D21", muted="#5C636B",
        fault="#D9480F", fault_soft="#FFE8D9", teal="#0B7285", teal_soft="#E3F4F6",
        blue="#1864AB", blue_soft="#E7F0FA", violet="#5F3DC4", violet_soft="#EEEBFB",
        slate="#495057", slate_soft="#EEF0F2", live="#2B8A3E", contra="#C92A2A", super="#7A828A",
        bar="#1A1D21", bar_ink="#FFFFFF"),
    "dark": dict(  # Strata Dark
        bg="#0F141A", card="#161C24", line="#2A323C", grid="#1C232C", ink="#E6EDF3", muted="#8D96A0",
        fault="#FF7A3D", fault_soft="#3A2216", teal="#3BC9DB", teal_soft="#0E2A2F",
        blue="#74C0FC", blue_soft="#13263A", violet="#B197FC", violet_soft="#231D3B",
        slate="#ADB5BD", slate_soft="#1F252D", live="#51CF66", contra="#FF6B6B", super="#9AA3AD",
        bar="#E6EDF3", bar_ink="#0F141A"),
}
ICON = "#E8590C"  # single-file icons: fault accent, legible on #FFFFFF and #0D1117

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def tw(s: str, size: float, bold: bool = False, mono: bool = False) -> float:
    """Rough text width; system fonts vary, so layouts leave slack."""
    return len(s) * size * (0.61 if mono else (0.58 if bold else 0.54))


def text(x, y, s, size=16, fill="ink", t=None, weight=400, anchor="start", mono=False, ls=None, opacity=None):
    color = t[fill] if t and fill in t else fill
    extra = f' letter-spacing="{ls}"' if ls is not None else ""
    extra += f' opacity="{opacity}"' if opacity is not None else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{MONO if mono else SANS}" font-size="{size}" '
            f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}"{extra}>{esc(s)}</text>')


def frame(w, h, t, body, title, desc):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-labelledby="t d">\n<title id="t">{esc(title)}</title><desc id="d">{esc(desc)}</desc>\n'
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="18" fill="{t["bg"]}" stroke="{t["line"]}"/>\n'
            f'{body}\n</svg>\n')


def markers(t, keys):
    return "<defs>" + "".join(
        f'<marker id="ar-{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{t[k]}"/></marker>' for k in keys) + "</defs>"


def arrow(x1, y1, x2, y2, t, color="muted", dash=False, width=1.8):
    d = ' stroke-dasharray="6 5"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{t[color]}" '
            f'stroke-width="{width}"{d} marker-end="url(#ar-{color})"/>')


def pill(cx, cy, s, t, size=12, fill="card", stroke="line", color="muted", mono=True, weight=600):
    w = tw(s, size, mono=mono) + 14
    return (f'<rect x="{cx - w / 2:.1f}" y="{cy - size * 0.95:.1f}" width="{w:.1f}" height="{size * 1.9:.1f}" '
            f'rx="{size * 0.95:.1f}" fill="{t[fill]}" stroke="{t[stroke]}"/>'
            + text(cx, cy + size * 0.36, s, size, color, t, weight, "middle", mono))


# State glyphs (rule 9: colour never carries meaning alone, so every state also has a shape and a word).
def glyph(kind, cx, cy, r, t):
    c = {"live": t["live"], "contradicted": t["contra"], "superseded": t["super"]}[kind]
    ring = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c}" stroke-width="2.2"/>'
    k = r * 0.45
    if kind == "live":
        mark = f'<path d="M{cx - k:.1f} {cy:.1f}l{k * 0.7:.1f} {k * 0.75:.1f}l{k * 1.35:.1f} -{k * 1.5:.1f}"'
    elif kind == "contradicted":
        mark = f'<path d="M{cx - k:.1f} {cy - k:.1f}L{cx + k:.1f} {cy + k:.1f}M{cx + k:.1f} {cy - k:.1f}L{cx - k:.1f} {cy + k:.1f}"'
    else:  # superseded: double chevron, "replaced by something newer"
        mark = (f'<path d="M{cx - k:.1f} {cy - k * 0.8:.1f}l{k * 0.8:.1f} {k * 0.8:.1f}l-{k * 0.8:.1f} {k * 0.8:.1f}'
                f'M{cx:.1f} {cy - k * 0.8:.1f}l{k * 0.8:.1f} {k * 0.8:.1f}l-{k * 0.8:.1f} {k * 0.8:.1f}"')
    return ring + mark + f' fill="none" stroke="{c}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'


# ---------------------------------------------------------------- hero
def hero(t):
    w, h = 1200, 360
    b = [f'<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">'
         f'<circle cx="2" cy="2" r="1.2" fill="{t["grid"]}"/></pattern>',
         f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="18" fill="url(#dots)"/>']
    # mark: two nodes split by a fault
    mx, my = 64, 70
    b.append(f'<rect x="{mx}" y="{my}" width="64" height="64" rx="16" fill="{t["fault"]}"/>'
             f'<circle cx="{mx + 18}" cy="{my + 22}" r="6" fill="{t["bg"]}"/><circle cx="{mx + 46}" cy="{my + 44}" r="6" fill="{t["bg"]}"/>'
             f'<path d="M{mx + 40} {my + 6}L{mx + 30} {my + 26}L{mx + 38} {my + 34}L{mx + 24} {my + 58}" fill="none" '
             f'stroke="{t["bg"]}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>')
    b.append(text(150, 124, "Faultline", 64, "ink", t, 750, ls=-1.5))
    b.append(text(66, 186, "Finds where an organisation's documented knowledge", 24, "ink", t, 500))
    b.append(text(66, 218, "contradicts itself, ranks every conflict by what sits", 24, "ink", t, 500))
    b.append(text(66, 250, "downstream of it, and repairs it.", 24, "ink", t, 500))
    x = 66
    for s, k in [("Graph Hacks 2026", "fault"), ("FalkorDB × WeMakeDevs", "teal"),
                 ("Track 03 · Company Brain", "blue"), ("Track 02 · Agent Memory", "violet")]:
        cw = tw(s, 14, bold=True) + 28
        b.append(f'<rect x="{x}" y="288" width="{cw:.1f}" height="32" rx="16" fill="{t[k + "_soft"]}" stroke="{t[k]}" stroke-opacity="0.45"/>'
                 + text(x + cw / 2, 309, s, 14, k, t, 650, "middle"))
        x += cw + 10
    # network art, split by the fault line
    nodes = {"a": (770, 92), "b": (720, 196), "c": (836, 250), "d": (868, 168),
             "e": (1010, 78), "f": (1086, 176), "g": (990, 262), "h": (1120, 292), "i": (950, 160)}
    edges = [("a", "b"), ("b", "c"), ("a", "d"), ("b", "d"), ("c", "d"), ("e", "f"), ("f", "g"), ("g", "h"),
             ("e", "i"), ("i", "g"), ("f", "h")]
    for p, q in edges:
        (x1, y1), (x2, y2) = nodes[p], nodes[q]
        b.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{t["muted"]}" stroke-opacity="0.55" stroke-width="2"/>')
    fault = "M930 18 L906 104 L944 150 L912 214 L952 262 L924 342"
    b.append(f'<path d="{fault}" fill="none" stroke="{t["fault"]}" stroke-width="10" stroke-opacity="0.16" stroke-linejoin="round"/>'
             f'<path d="{fault}" fill="none" stroke="{t["fault"]}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')
    # the contradiction across the fault
    (x1, y1), (x2, y2) = nodes["d"], nodes["i"]
    b.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{t["contra"]}" stroke-width="2.4" stroke-dasharray="5 5"/>')
    for k, (x0, y0) in nodes.items():
        hot = k in ("d", "i")
        b.append(f'<circle cx="{x0}" cy="{y0}" r="{13 if hot else 9}" fill="{t["card"]}" '
                 f'stroke="{t["fault"] if hot else t["teal"]}" stroke-width="{3 if hot else 2.4}"/>')
    b.append(pill(908, 130, "CONTRADICTS", t, 11, "card", "line", "contra"))
    return frame(w, h, t, "\n".join(b), "Faultline",
                 "Faultline finds where documented knowledge contradicts itself. A small graph is split by a fault line; "
                 "two claims on either side are joined by a CONTRADICTS edge.")


# ---------------------------------------------------------------- stack strip
def stack(t):
    items = [("Python 3.12", "blue"), ("FastAPI", "teal"), ("FalkorDB · raw Cypher", "fault"), ("Gemini free tier", "violet"),
             ("Groq overflow", "violet"), ("Vite + React + TS", "blue"), ("Cytoscape.js", "teal"), ("$0 budget", "slate")]
    widths = [tw(s, 15, bold=True) + 44 for s, _ in items]
    gap, total = 10, 0
    total = sum(widths) + gap * (len(items) - 1)
    w, h = max(1200, int(total + 48)), 72
    x, b = (w - total) / 2, []
    for (s, k), cw in zip(items, widths):
        b.append(f'<rect x="{x:.1f}" y="18" width="{cw:.1f}" height="36" rx="18" fill="{t["card"]}" stroke="{t["line"]}"/>'
                 f'<circle cx="{x + 19:.1f}" cy="36" r="5" fill="{t[k]}"/>' + text(x + 32, 41.5, s, 15, "ink", t, 600))
        x += cw + gap
    return frame(w, h, t, "\n".join(b), "Stack", "Python 3.12, FastAPI, FalkorDB with raw Cypher, Gemini free tier, "
                 "Groq overflow, Vite React TypeScript, Cytoscape.js, zero budget.")


# ---------------------------------------------------------------- funnel
def funnel(t):
    w, h = 1200, 560
    f = FUNNEL
    rows = [("STAGE 1", "All possible pairs", "n·(n−1)/2 · counted, never enumerated", f["naive"], "solid"),
            ("STAGE 2", "Graph collapse", "shared Entity · Cypher §7.1", f["collapsed"], "solid"),
            ("STAGE 3", "Deterministic prefilter", "same predicate · object or polarity differs", f["prefiltered"], "solid"),
            ("STAGE 4", "LLM judgement", "Adjudicator · every call cached", f["judged_max"], "dashed")]
    cx, maxw, minw = 770, 620, 150
    b = [markers(t, ["muted"])]
    for i, (stage, name, mech, n, style) in enumerate(rows):
        y = 44 + i * 112
        bw = minw + (maxw - minw) * math.log(n) / math.log(f["naive"])
        b.append(text(56, y + 22, stage, 13, "fault", t, 700, ls=1.6))
        b.append(text(56, y + 50, name, 23, "ink", t, 650))
        b.append(text(56, y + 76, mech, 15, "muted", t))
        if style == "solid":
            b.append(f'<rect x="{cx - bw / 2:.1f}" y="{y}" width="{bw:.1f}" height="88" rx="14" fill="{t["bar"]}" '
                     f'fill-opacity="{1 - i * 0.12:.2f}"/>')
            b.append(text(cx, y + 58, f"{n:,}", 40, "bar_ink", t, 750, "middle"))
        else:
            b.append(f'<rect x="{cx - bw / 2:.1f}" y="{y + 1}" width="{bw:.1f}" height="86" rx="14" fill="none" '
                     f'stroke="{t["bar"]}" stroke-width="2" stroke-dasharray="7 6"/>')
            b.append(text(cx, y + 58, f"≤ {n}", 40, "ink", t, 750, "middle"))
        if i < 3:
            b.append(arrow(cx, y + 92, cx, y + 108, t))
    rx = 1146
    b.append(f'<path d="M{rx - 14} 88 H{rx} V{44 + 2 * 112 + 44} H{rx - 14}" fill="none" stroke="{t["fault"]}" stroke-width="2"/>')
    red = f["naive"] / f["prefiltered"]
    b.append(f'<g transform="translate({rx + 18} {44 + 112 + 44}) rotate(90)">'
             + text(0, 0, f"{red:.0f}× fewer", 15, "fault", t, 700, "middle") + "</g>")
    b.append(text(56, h - 22, f"Measured on the {f['claims']}-claim, {f['entities']}-entity synthetic graph by "
                  "python -m graph.collapse_demo. Stage 4 is an upper bound until the Adjudicator lands.", 14, "muted", t))
    return frame(w, h, t, "\n".join(b), "The four-stage funnel",
                 f"Measured on a synthetic graph: {f['naive']} possible pairs, {f['collapsed']} after the graph collapse, "
                 f"{f['prefiltered']} after the deterministic prefilter, at most {f['judged_max']} LLM calls.")


# ---------------------------------------------------------------- architecture
def box(cx, cy, w, h, title, sub, t, k="slate", sub2=None):
    out = (f'<rect x="{cx - w / 2:.1f}" y="{cy - h / 2:.1f}" width="{w}" height="{h}" rx="14" fill="{t[k + "_soft"]}" '
           f'stroke="{t[k]}" stroke-width="1.6"/>' + text(cx, cy - (8 if sub2 else 2), title, 17, "ink", t, 700, "middle"))
    if sub:
        out += text(cx, cy + (14 if sub2 else 20), sub, 13, "muted", t, 500, "middle")
    if sub2:
        out += text(cx, cy + 32, sub2, 13, "muted", t, 500, "middle")
    return out


def disk_badge(x, y, t, label="cached"):
    return (f'<g transform="translate({x} {y})"><ellipse cx="8" cy="3" rx="8" ry="3" fill="none" stroke="{t["fault"]}" stroke-width="1.6"/>'
            f'<path d="M0 3v9c0 1.7 3.6 3 8 3s8-1.3 8-3V3" fill="none" stroke="{t["fault"]}" stroke-width="1.6"/>'
            + text(22, 13, label, 12, "fault", t, 700) + "</g>")


def architecture(t):
    w, h = 1200, 470
    b = [markers(t, ["muted", "fault"])]
    top, bot = 140, 360
    b.append(text(60, 54, "INGEST AND SERVE", 13, "muted", t, 700, ls=1.6))
    b.append(text(60, 284, "THE FUNNEL", 13, "muted", t, 700, ls=1.6))
    # sources stack
    for i, s in enumerate(["Documents", "Messages", "Tickets"]):
        y = top - 44 + i * 44
        b.append(f'<rect x="40" y="{y - 17}" width="150" height="34" rx="10" fill="{t["blue_soft"]}" stroke="{t["blue"]}" stroke-width="1.4"/>'
                 + text(115, y + 5, s, 14, "ink", t, 600, "middle"))
    b.append(arrow(194, top, 262, top, t))
    b.append(box(370, top, 200, 104, "Surveyor", "claim extraction", t, "violet", "Gemini · Groq overflow"))
    b.append(disk_badge(318, top + 62, t))
    b.append(arrow(474, top, 536, top, t))
    # FalkorDB cylinder
    cx, cw = 640, 196
    b.append(f'<path d="M{cx - cw / 2} {top - 44}v88c0 10 44 18 {cw / 2} 18s{cw / 2}-8 {cw / 2}-18v-88" fill="{t["fault_soft"]}" stroke="{t["fault"]}" stroke-width="1.8"/>'
             f'<ellipse cx="{cx}" cy="{top - 44}" rx="{cw / 2}" ry="18" fill="{t["card"]}" stroke="{t["fault"]}" stroke-width="1.8"/>')
    b.append(text(cx, top + 8, "FalkorDB", 19, "ink", t, 750, "middle"))
    b.append(text(cx, top + 32, "faultline:{tenant}", 13, "fault", t, 600, "middle", mono=True))
    b.append(arrow(744, top, 806, top, t))
    b.append(box(910, top, 196, 104, "FastAPI + MCP", "one process", t, "teal", "HTTP §9 · tools §8"))
    b.append(arrow(1012, top, 1046, top, t))
    b.append(f'<rect x="1050" y="{top - 52}" width="112" height="104" rx="14" fill="{t["blue_soft"]}" stroke="{t["blue"]}" stroke-width="1.6"/>'
             + text(1106, top - 6, "Web UI", 17, "ink", t, 700, "middle") + text(1106, top + 16, "ranked queue", 12, "muted", t, 500, "middle")
             + text(1106, top + 32, "path ≤ 40 nodes", 12, "muted", t, 500, "middle"))
    # funnel row
    b.append(arrow(600, top + 64, 470, bot - 52, t, "fault"))
    b.append(box(400, bot, 210, 96, "Collapse", "stage 2 · Cypher §7.1", t, "fault", "shared Entity only"))
    b.append(arrow(507, bot, 571, bot, t))
    b.append(box(680, bot, 210, 96, "Prefilter", "stage 3 · Python", t, "slate", "no model call, free"))
    b.append(arrow(787, bot, 851, bot, t))
    b.append(box(960, bot, 210, 96, "Adjudicator", "stage 4 · LLM judge", t, "violet", "precedent first §7.4"))
    b.append(disk_badge(1078, bot + 30, t))
    b.append(arrow(905, bot - 50, 700, top + 70, t, "fault"))
    b.append(pill(820, 262, "writes CONTRADICTS · Conflict · blast radius", t, 11, "card", "line", "fault"))
    return frame(w, h, t, "\n".join(b), "Architecture",
                 "Documents, messages and tickets flow into the Surveyor, which extracts claims into FalkorDB. "
                 "The funnel reads from FalkorDB: graph collapse, deterministic prefilter, then the Adjudicator, "
                 "which writes CONTRADICTS edges and Conflicts back. FastAPI and MCP serve the ranked queue to the web UI.")


# ---------------------------------------------------------------- graph model
def graph_model(t):
    w, h = 1200, 680
    W, H = 184, 72
    N = {"Person": (112, 340, "slate", "name · role · active"),
         "Document": (380, 340, "blue", "title · path · kind"),
         "Claim": (680, 340, "fault", "predicate · object · polarity"),
         "Entity": (1000, 340, "teal", "one per real subject"),
         "Decision": (380, 120, "violet", "ref · status"),
         "Message": (680, 120, "blue", "channel · text"),
         "Ticket": (1000, 120, "blue", "ref · title · text"),
         "System": (380, 562, "slate", "tier 1–3"),
         "Conflict": (680, 562, "fault", "kind · status · blast_radius")}
    b = [markers(t, ["muted", "contra"])]

    def edge(x1, y1, x2, y2, label, lx, ly):
        return arrow(x1, y1, x2, y2, t) + pill(lx, ly, label, t, 11.5)

    L, R, T, B = (lambda k: N[k][0] - W / 2), (lambda k: N[k][0] + W / 2), (lambda k: N[k][1] - H / 2), (lambda k: N[k][1] + H / 2)
    b.append(edge(R("Document"), 340, L("Claim") - 2, 340, "ASSERTS", 530, 340))
    b.append(edge(R("Claim"), 340, L("Entity") - 2, 340, "ABOUT", 840, 340))
    # Message and Ticket each have an edge in both directions; labels sit on their own line.
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
    # self loops
    dx, dy = L("Decision"), 120
    b.append(f'<path d="M{dx} {dy - 14} C{dx - 70} {dy - 50}, {dx - 70} {dy + 50}, {dx - 2} {dy + 14}" fill="none" '
             f'stroke="{t["muted"]}" stroke-width="1.8" marker-end="url(#ar-muted)"/>' + pill(dx - 30, dy - 52, "SUPERSEDES", t, 11.5))
    cx_, cy_ = R("Claim"), B("Claim")
    b.append(f'<path d="M{cx_ - 30} {cy_} C{cx_ - 20} {cy_ + 70}, {cx_ + 70} {cy_ + 40}, {cx_ + 2} {cy_ - 12}" fill="none" '
             f'stroke="{t["contra"]}" stroke-width="2" marker-end="url(#ar-contra)"/>' + pill(cx_ + 74, cy_ + 46, "CONTRADICTS", t, 11.5, color="contra"))
    for name, (x, y, k, props) in N.items():
        b.append(f'<rect x="{x - W / 2}" y="{y - H / 2}" width="{W}" height="{H}" rx="14" fill="{t[k + "_soft"]}" stroke="{t[k]}" stroke-width="1.8"/>'
                 + text(x, y - 3, name, 18, "ink", t, 750, "middle") + text(x, y + 20, props, 12, "muted", t, 500, "middle"))
    # legend card
    lx, ly = 902, 528
    b.append(f'<rect x="{lx}" y="{ly}" width="248" height="104" rx="12" fill="{t["card"]}" stroke="{t["line"]}"/>'
             + text(lx + 16, ly + 26, "9 labels · 11 edge types", 14, "ink", t, 700)
             + text(lx + 16, ly + 50, "arrows point From → To", 13, "muted", t)
             + text(lx + 16, ly + 72, "one graph per tenant:", 13, "muted", t)
             + text(lx + 16, ly + 92, "faultline:{tenant_id}", 13, "fault", t, 600, mono=True))
    return frame(w, h, t, "\n".join(b), "Graph model",
                 "Nine node labels and eleven edge types. Documents, messages and tickets ASSERT claims; claims are ABOUT exactly "
                 "one Entity; claims CONTRADICT claims; Conflicts INVOLVE and RESOLVE_AS claims; documents CITE decisions and "
                 "GOVERN systems; decisions SUPERSEDE decisions; people AUTHOR documents and decisions and OWN systems.")


# ---------------------------------------------------------------- supersedes (demo case 2)
def supersedes(t):
    w, h = 1200, 500
    b = [markers(t, ["muted", "violet"])]
    # documents
    docs = [(250, "Cold Chain Excursion Runbook", "updated 29 Sep 2026  ·  newer", "reject after 30 min above 8 °C", "superseded"),
            (950, "Cold Chain Policy v3", "updated 9 Mar 2026  ·  older", "reject after 15 min above 8 °C", "live")]
    for x, title, upd, claim, state in docs:
        b.append(f'<rect x="{x - 210}" y="40" width="420" height="124" rx="14" fill="{t["blue_soft"]}" stroke="{t["blue"]}" stroke-width="1.6"/>'
                 + text(x - 186, 74, title, 18, "ink", t, 700) + text(x - 186, 98, upd, 13, "muted", t, 500, mono=True))
        b.append(glyph(state, x - 172, 134, 11, t) + text(x - 152, 139, claim, 15, "ink", t, 600))
    # decision chain
    adrs = [(250, "ADR-41", "superseded", "30 min, all loads"), (600, "ADR-63", "superseded", "20 min pharma"),
            (950, "ADR-88", "live", "15 min, all loads")]
    for x, ref, state, gist in adrs:
        b.append(f'<rect x="{x - 120}" y="236" width="240" height="78" rx="14" fill="{t["violet_soft"]}" stroke="{t["violet"]}" stroke-width="1.6"/>'
                 + glyph(state, x - 92, 275, 11, t) + text(x - 70, 270, ref, 18, "ink", t, 750)
                 + text(x - 70, 293, f"{state} · {gist}", 12.5, "muted", t, 500))
    b.append(arrow(830, 275, 722, 275, t, "violet", width=2.2) + pill(776, 252, "SUPERSEDES", t, 11, color="violet"))
    b.append(arrow(480, 275, 372, 275, t, "violet", width=2.2) + pill(426, 252, "SUPERSEDES", t, 11, color="violet"))
    b.append(arrow(250, 166, 250, 232, t, dash=True) + pill(296, 200, "CITES", t, 11))
    b.append(arrow(950, 166, 950, 232, t, dash=True) + pill(996, 200, "CITES", t, 11))
    # verdicts
    rows = [("contradicted", "Timestamp logic", "the newest document wins → Runbook → 30 min", "WRONG"),
            ("live", "Traversal §7.2", "walk SUPERSEDES to the decision nothing supersedes → ADR-88 → 15 min", "RIGHT")]
    for i, (kind, head, body, verdict) in enumerate(rows):
        y = 356 + i * 62
        b.append(f'<rect x="40" y="{y}" width="1120" height="50" rx="12" fill="{t["card"]}" stroke="{t["line"]}"/>'
                 + glyph(kind, 70, y + 25, 12, t) + text(94, y + 31, head, 16, "ink", t, 700)
                 + text(248, y + 31, body, 15, "muted", t, 500)
                 + text(1136, y + 31, verdict, 14, "live" if kind == "live" else "contra", t, 800, "end", ls=1.2))
    return frame(w, h, t, "\n".join(b), "Adjudication by traversal, not timestamp",
                 "The runbook was updated more recently but cites ADR-41, which ADR-63 and then ADR-88 supersede. "
                 "Timestamp logic picks the runbook's 30 minutes, which is wrong. Walking SUPERSEDES picks ADR-88's 15 minutes.")


# ---------------------------------------------------------------- states legend
def states(t):
    w, h = 1200, 96
    b = []
    items = [("live", "Live", "current, nothing contradicts it"), ("contradicted", "Contradicted", "in an open conflict"),
             ("superseded", "Superseded", "a newer decision replaced it")]
    for i, (k, word, gloss) in enumerate(items):
        x = 48 + i * 380
        b.append(glyph(k, x + 16, 48, 14, t) + text(x + 42, 46, word, 18, "ink", t, 700) + text(x + 42, 68, gloss, 13.5, "muted", t))
    return frame(w, h, t, "\n".join(b), "Claim states",
                 "Live: a check in a circle. Contradicted: a cross in a circle. Superseded: a double chevron in a circle.")


# ---------------------------------------------------------------- icons (single file each)
ICONS = {
    "funnel": '<path d="M3 4h18l-7 8.5V19l-4 2v-8.5z"/>',
    "flow": '<rect x="2.5" y="4" width="6" height="6" rx="1.5"/><rect x="15.5" y="4" width="6" height="6" rx="1.5"/>'
            '<rect x="9" y="15" width="6" height="6" rx="1.5"/><path d="M8.5 7h7M18.5 10v3l-3.5 3M5.5 10v3l3.5 3"/>',
    "graph": '<circle cx="5" cy="6" r="2.5"/><circle cx="19" cy="6" r="2.5"/><circle cx="12" cy="18" r="2.5"/>'
             '<path d="M7.5 6h9M6.3 8.2l4.4 7.6M17.7 8.2l-4.4 7.6"/>',
    "query": '<path d="M8 6l-5.5 6L8 18M16 6l5.5 6L16 18M13.5 4l-3 16"/>',
    "gauge": '<path d="M3.5 17a8.5 8.5 0 1 1 17 0"/><path d="M12 17l4.5-6"/><circle cx="12" cy="17" r="1.6"/>',
    "states": '<circle cx="12" cy="12" r="9"/><path d="M8 12.3l2.7 2.7L16.5 9"/>',
    "terminal": '<rect x="2.5" y="4" width="19" height="16" rx="2.5"/><path d="M6.5 9.5l3 2.5-3 2.5M12 15h5"/>',
    "key": '<circle cx="8" cy="15" r="4.5"/><path d="M11.2 11.8L20 3M16.5 6.5l2.5 2.5M14 9l2 2"/>',
    "tree": '<path d="M4 3v15a2 2 0 0 0 2 2h4M4 9h6M4 15h6"/><rect x="11" y="6.5" width="9" height="5" rx="1.2"/>'
            '<rect x="11" y="12.5" width="9" height="5" rx="1.2"/><rect x="11" y="18.5" width="9" height="3" rx="1"/>',
    "status": '<path d="M9 6h11M9 12h11M9 18h11"/><path d="M3 6l1.5 1.5L7 5M3 12l1.5 1.5L7 11"/><circle cx="4.8" cy="18" r="1.6"/>',
    "shield": '<path d="M12 2.5l8 3v6c0 5-3.4 8.6-8 10-4.6-1.4-8-5-8-10v-6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    "chain": '<rect x="2.5" y="9" width="5.5" height="6" rx="1.4"/><rect x="9.25" y="9" width="5.5" height="6" rx="1.4"/>'
             '<rect x="16" y="9" width="5.5" height="6" rx="1.4"/><path d="M5.25 9V6h13.5v3"/>',
}


def icon(body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
            f'stroke="{ICON}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{body}</svg>\n')


def main():
    for name, fn in [("hero", hero), ("stack", stack), ("funnel", funnel), ("architecture", architecture),
                     ("graph-model", graph_model), ("supersedes", supersedes), ("states", states)]:
        for theme, t in THEMES.items():
            (OUT / f"{name}-{theme}.svg").write_text(fn(t), encoding="utf-8", newline="\n")
    for name, body in ICONS.items():
        (OUT / f"icon-{name}.svg").write_text(icon(body), encoding="utf-8", newline="\n")
    print(f"wrote {len(list(OUT.glob('*.svg')))} svgs to {OUT}")


if __name__ == "__main__":
    main()
