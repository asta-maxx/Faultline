import { useCallback, useEffect, useMemo, useRef } from 'react'
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'
import type { ClaimState, NodeType } from '../../types'
import { canvasLabel, dateBands, type Band, type GraphModel } from '../../lib/graphModel'
import { iconDataUri } from '../../lib/icons'
import styles from './TraversalGraph.module.css'

cytoscape.use(dagre)

interface Props {
  model: GraphModel
  selectedId: string | null
  onSelect: (id: string | null) => void
}

const NODE = 36 // square node, px at zoom 1
const ROW = 84 // vertical pitch of stacked nodes: box + two label lines + air
const BAND_GAP = 24 // air between bands, where the separator sits
const SIDE_PITCH = 56 // vertical pitch in the side columns, whose labels sit to the right
const ENTITY_GAP = 120 // from the rightmost claim to the claims' Entity
const SYSTEM_GAP = 150 // from the dated part (and the Entity) to the systems column
const PERSON_GAP = 300 // systems column to their owners: system label width + room for the OWNS label
const MAX_ZOOM = 1.25
const PAD = 24

export function TraversalGraph({ model, selectedId, onSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  // Gutter labels and band separators, keyed "label:<band>" and "rule:<band>".
  const overlayRefs = useRef(new Map<string, HTMLSpanElement>())
  const cyRef = useRef<cytoscape.Core | null>(null)
  const onSelectRef = useRef(onSelect)
  const selectedRef = useRef(selectedId)
  // The band list depends only on the data; their positions depend on the viewport.
  const bands = useMemo(() => dateBands(model.nodes), [model])

  useEffect(() => {
    onSelectRef.current = onSelect
  }, [onSelect])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    let cy: cytoscape.Core | null = null
    let disposed = false

    // Positions are written straight to the overlay's DOM from Cytoscape's own
    // render event, read back from the rendered node boxes, so the gutter moves
    // in the same frame as the canvas and never waits on a React render.
    const project = () => {
      const core = cy
      if (!core) return
      let previousBottom: number | null = null
      for (const band of bands) {
        const ids = new Set(band.nodeIds)
        const nodes = core.nodes().filter((n) => ids.has(n.id()))
        const top = nodes.renderedBoundingBox({ includeLabels: false }).y1
        const bottom = nodes.renderedBoundingBox({ includeLabels: true }).y2
        const label = overlayRefs.current.get(`label:${band.key}`)
        if (label) label.style.transform = `translateY(${Math.round(top)}px)`
        const rule = overlayRefs.current.get(`rule:${band.key}`)
        if (rule && previousBottom !== null) {
          rule.style.transform = `translateY(${Math.round((previousBottom + top) / 2)}px)`
        }
        previousBottom = bottom
      }
    }

    // Fit, then cap the zoom so a small path does not blow up to poster size.
    const fitView = () => {
      if (!cy) return
      cy.fit(undefined, PAD)
      if (cy.zoom() > MAX_ZOOM) {
        cy.zoom(MAX_ZOOM)
        cy.center()
      }
    }

    // Canvas text does not wait for web fonts, and the panels around the canvas
    // reflow when Spectral and Plex arrive. Start once every font has settled.
    Promise.all([document.fonts.load('400 10px "JetBrains Mono"'), document.fonts.ready])
      .catch(() => undefined)
      .then(() => {
        if (disposed) return
        const palette = readPalette()
        cy = cytoscape({
          container,
          elements: elements(model, palette),
          style: stylesheet(palette),
          layout: { name: 'preset' },
          minZoom: 0.2,
          maxZoom: 2,
          boxSelectionEnabled: false,
          autoungrabify: true,
        })
        cyRef.current = cy
        cy.on('render', project)
        cy.on('tap', 'node', (evt) => onSelectRef.current(evt.target.id()))
        cy.on('tap', (evt) => {
          if (evt.target === cy) onSelectRef.current(null)
        })

        layoutWithDateGutter(cy, model, bands)
        fitView()
        if (selectedRef.current) cy.getElementById(selectedRef.current).select()
      })

    const resize = new ResizeObserver(() => {
      if (!cy) return
      cy.resize()
      fitView()
    })
    resize.observe(container)

    return () => {
      disposed = true
      resize.disconnect()
      cy?.destroy()
      cyRef.current = null
    }
  }, [model, bands])

  // Selection follows the inspector, including selections made from inside it.
  useEffect(() => {
    selectedRef.current = selectedId
    const cy = cyRef.current
    if (!cy) return
    cy.nodes().unselect()
    if (selectedId) cy.getElementById(selectedId).select()
  }, [selectedId])

  // Returns a callback ref; the map is only touched when React attaches or detaches.
  const overlayRef = useCallback(
    (key: string) => (el: HTMLSpanElement | null) => {
      if (el) overlayRefs.current.set(key, el)
      else overlayRefs.current.delete(key)
    },
    [],
  )

  return (
    <div className={styles.frame}>
      <div className={styles.gutter} aria-hidden="true">
        {bands.map((b) => (
          <span key={b.key} ref={overlayRef(`label:${b.key}`)} className={styles.bandLabel}>
            {b.month ?? 'undated'}
          </span>
        ))}
      </div>
      <div className={styles.canvasWrap}>
        <div ref={containerRef} className={styles.canvas} role="img" aria-label={describe(model)} />
      </div>
      <div className={styles.separators} aria-hidden="true">
        {bands.slice(1).map((b) => (
          <span key={b.key} ref={overlayRef(`rule:${b.key}`)} />
        ))}
      </div>
    </div>
  )
}

// ── Layout ───────────────────────────────────────────────────────────────────

/**
 * Dagre (left to right) decides each dated node's column: causality runs across.
 * Each node's own date then decides its row: time runs down, newest at the top,
 * one band per month, then an undated band. Nodes sharing a column in a band stack.
 *
 * Nodes with no date in §5 sit to the right in side columns, each placed level with
 * what it connects to so edges stay short and do not cross the drawing:
 *   Entity  next to the claims it is ABOUT
 *   System  one column, each at the height of the documents that GOVERN it
 *   Person  next to the systems it OWNS
 * Within a side column, nodes keep their preferred height where they can and are
 * pushed apart just enough not to overlap.
 */
function layoutWithDateGutter(cy: cytoscape.Core, model: GraphModel, bands: Band[]): void {
  cy.layout({
    name: 'dagre',
    rankDir: 'LR',
    rankSep: 56,
    nodeSep: 16,
    nodeDimensionsIncludeLabels: true,
    fit: false,
    animate: false,
  } as cytoscape.LayoutOptions).run()

  const xs = new Map<string, number>()
  cy.nodes().forEach((n) => {
    xs.set(n.id(), n.position('x'))
  })

  const ys = new Map<string, number>()
  let top = 0
  let maxX = -Infinity
  for (const band of bands) {
    const columns = clusterColumns(band, xs)
    const depth = Math.max(...columns.map((c) => c.length))
    columns.forEach((column) => {
      column
        .sort((a, b) => order(model, a) - order(model, b))
        .forEach((id, i) => {
          const x = xs.get(id) ?? 0
          const y = top + i * ROW + NODE / 2
          maxX = Math.max(maxX, x)
          ys.set(id, y)
          cy.getElementById(id).position({ x, y })
        })
    })
    top += depth * ROW + BAND_GAP
  }
  if (!Number.isFinite(maxX)) maxX = 0

  const neighbours = (id: string, type: NodeType) =>
    model.edges
      .flatMap((e) => (e.source === id ? [e.target] : e.target === id ? [e.source] : []))
      .filter((other) => model.byId.get(other)?.type === type)

  // Entity: right of its claims, level with them; nudged off their row when they
  // share one, so its ABOUT edges do not run along the CONTRADICTS line.
  let rightEdge = maxX
  for (const e of model.nodes.filter((n) => n.type === 'entity')) {
    const claims = neighbours(e.id, 'claim')
    const cys = claims.map((c) => ys.get(c) ?? 0)
    const sameRow = cys.length > 1 && cys.every((y) => y === cys[0])
    const x = Math.max(maxX - ENTITY_GAP, ...claims.map((c) => xs.get(c) ?? 0)) + ENTITY_GAP
    const y = mean(cys, NODE / 2) + (sameRow ? ROW / 2 : 0)
    rightEdge = Math.max(rightEdge, x)
    ys.set(e.id, y)
    cy.getElementById(e.id).position({ x, y })
  }

  // Systems: one column, each at the mean height of what points at it.
  const systemsX = rightEdge + SYSTEM_GAP
  placeColumn(
    cy,
    ys,
    systemsX,
    model.nodes
      .filter((n) => n.type === 'system')
      .map((n) => ({
        id: n.id,
        want: mean([...neighbours(n.id, 'document'), ...neighbours(n.id, 'entity')].map((d) => ys.get(d) ?? 0), 0),
      })),
  )

  // People: next to the systems they own.
  placeColumn(
    cy,
    ys,
    systemsX + PERSON_GAP,
    model.nodes
      .filter((n) => n.type === 'person')
      .map((n) => ({ id: n.id, want: mean(neighbours(n.id, 'system').map((sid) => ys.get(sid) ?? 0), 0) })),
  )
}

/** One column at x: each node at its preferred height, pushed apart to SIDE_PITCH, recentred. */
function placeColumn(cy: cytoscape.Core, ys: Map<string, number>, x: number, items: { id: string; want: number }[]): void {
  const sorted = [...items].sort((a, b) => a.want - b.want || a.id.localeCompare(b.id))
  const placed: number[] = []
  sorted.forEach((item, i) => {
    placed[i] = i === 0 ? item.want : Math.max(item.want, placed[i - 1] + SIDE_PITCH)
  })
  // Pushing only downwards drifts the column below what it serves; centre it back.
  const drift = mean(placed, 0) - mean(sorted.map((s) => s.want), 0)
  sorted.forEach((item, i) => {
    const y = placed[i] - drift
    ys.set(item.id, y)
    cy.getElementById(item.id).position({ x, y })
  })
}

function mean(values: number[], fallback: number): number {
  return values.length ? values.reduce((a, b) => a + b, 0) / values.length : fallback
}

/** Groups a band's nodes into columns by their dagre x. */
function clusterColumns(band: Band, xs: Map<string, number>): string[][] {
  const sorted = [...band.nodeIds].sort((a, b) => (xs.get(a) ?? 0) - (xs.get(b) ?? 0))
  const columns: string[][] = []
  let lastX = -Infinity
  for (const id of sorted) {
    const x = xs.get(id) ?? 0
    if (x - lastX > NODE) columns.push([id])
    else columns[columns.length - 1].push(id)
    lastX = x
  }
  return columns
}

const TYPE_RANK: Record<NodeType, number> = {
  conflict: 0,
  claim: 1,
  document: 2,
  decision: 3,
  entity: 4,
  system: 5,
  person: 6,
  message: 7,
  ticket: 8,
}

function order(model: GraphModel, id: string): number {
  const n = model.byId.get(id)
  return n ? TYPE_RANK[n.type] : 99
}

// ── Elements and style ───────────────────────────────────────────────────────

interface Palette {
  base: string
  raised: string
  ink: string
  muted: string
  rule: string
  live: string
  contradicted: string
  superseded: string
}

function readPalette(): Palette {
  const css = getComputedStyle(document.documentElement)
  const v = (name: string) => css.getPropertyValue(name).trim()
  return {
    base: v('--surface-base'),
    raised: v('--surface-raised'),
    ink: v('--ink'),
    muted: v('--ink-muted'),
    rule: v('--rule'),
    live: v('--state-live'),
    contradicted: v('--state-contradicted'),
    superseded: v('--state-superseded'),
  }
}

function stateColor(state: ClaimState | undefined, p: Palette): string {
  if (state === 'live') return p.live
  if (state === 'contradicted') return p.contradicted
  if (state === 'superseded') return p.superseded
  return p.muted
}

function elements(model: GraphModel, p: Palette): cytoscape.ElementDefinition[] {
  const nodes = model.nodes.map((n) => {
    const colour = stateColor(n.state, p)
    return {
      data: {
        id: n.id,
        label: canvasLabel(n),
        state: n.state ?? 'none',
        // Systems and people stack tightly in side columns, so their labels sit to the right.
        side: n.type === 'system' || n.type === 'person' ? 'yes' : 'no',
        border: colour,
        icon: iconDataUri(n.type, n.state ? colour : p.ink),
      },
    }
  })
  // A fan of same-type edges from one node (a document GOVERNS three systems) is labelled
  // once: the type still reads on the lines, without a stack of identical labels.
  const labelled = new Set<string>()
  const edges = model.edges.map((e) => {
    const fan = `${e.source}|${e.type}`
    const label = labelled.has(fan) ? '' : e.type
    labelled.add(fan)
    return { data: { id: `${e.source}|${e.type}|${e.target}`, source: e.source, target: e.target, type: e.type, label } }
  })
  return [...nodes, ...edges]
}

function stylesheet(p: Palette): cytoscape.StylesheetJson {
  return [
    {
      selector: 'node',
      style: {
        shape: 'rectangle',
        width: NODE,
        height: NODE,
        'background-color': p.raised,
        'border-width': 1,
        'border-color': 'data(border)',
        'background-image': 'data(icon)',
        'background-width': '52%',
        'background-height': '52%',
        label: 'data(label)',
        color: p.ink,
        'font-family': '"JetBrains Mono", ui-monospace, monospace',
        'font-size': 10,
        'line-height': 1.45,
        'text-valign': 'bottom',
        'text-halign': 'center',
        'text-margin-y': 5,
        'text-wrap': 'wrap',
        'text-max-width': '128px',
        'text-justification': 'center',
        // A plate behind the text so a line passing under a label never strikes through it.
        'text-background-color': p.base,
        'text-background-opacity': 0.9,
        'text-background-padding': '2px',
      },
    },
    {
      // Side columns: the label goes to the right so nodes can stack tightly.
      selector: 'node[side = "yes"]',
      style: {
        'text-valign': 'center',
        'text-halign': 'right',
        'text-margin-x': 8,
        'text-margin-y': 0,
        'text-justification': 'left',
        'text-max-width': '180px',
      },
    },
    { selector: 'node[state = "superseded"]', style: { opacity: 0.35 } },
    {
      selector: 'node:selected',
      style: { 'border-width': 2, 'border-color': p.ink, 'overlay-opacity': 0 },
    },
    {
      selector: 'edge',
      style: {
        width: 1,
        // Each edge takes its own curve: no shared lanes, so labels do not pile up.
        'curve-style': 'bezier',
        'control-point-step-size': 28,
        'line-color': p.muted,
        'line-opacity': 0.7,
        'target-arrow-shape': 'triangle',
        'target-arrow-color': p.muted,
        'arrow-scale': 0.7,
        label: 'data(label)',
        color: p.muted,
        'font-family': '"JetBrains Mono", ui-monospace, monospace',
        'font-size': 9,
        'text-background-color': p.base,
        'text-background-opacity': 1,
        'text-background-padding': '2px',
        // Labels too small to read are dropped rather than drawn as noise.
        'min-zoomed-font-size': 7,
        'overlay-opacity': 0,
      },
    },
    {
      selector: 'edge[type = "CONTRADICTS"]',
      style: {
        'line-color': p.contradicted,
        'target-arrow-color': p.contradicted,
        'line-style': 'dashed',
        'line-dash-pattern': [6, 4],
        'line-opacity': 1,
        width: 1.5,
        color: p.contradicted,
      },
    },
  ]
}

function describe(model: GraphModel): string {
  const parts = model.typeCounts.map((t) => `${t.count} ${t.type}`)
  return `Traversal path: ${model.nodes.length} nodes (${parts.join(', ')}) and ${model.edges.length} edges.`
}
