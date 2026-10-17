import { useCallback, useEffect, useMemo, useRef } from 'react'
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'
import type { ClaimState, NodeType } from '../../types'
import { canvasLabel, dateBands, TIMELESS, type Band, type GraphModel } from '../../lib/graphModel'
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
const TIMELESS_GAP = 140 // from the last dated column to the timeless columns
const TIMELESS_PITCH = 144 // between timeless columns: label width + air
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
 * Dagre (left to right) decides each node's column: causality runs across.
 * Each node's own date then decides its row: time runs down, newest at the top,
 * one band per month, then an undated band. Nodes that share a column inside
 * one band stack vertically. Timeless nodes (no date property in §5) take a
 * column of their own on the right, spanning every band.
 */
function layoutWithDateGutter(cy: cytoscape.Core, model: GraphModel, bands: Band[]): void {
  cy.layout({
    name: 'dagre',
    rankDir: 'LR',
    rankSep: 44,
    nodeSep: 16,
    nodeDimensionsIncludeLabels: true,
    fit: false,
    animate: false,
  } as cytoscape.LayoutOptions).run()

  const xs = new Map<string, number>()
  cy.nodes().forEach((n) => {
    xs.set(n.id(), n.position('x'))
  })

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
          maxX = Math.max(maxX, x)
          cy.getElementById(id).position({ x, y: top + i * ROW + NODE / 2 })
        })
    })
    top += depth * ROW + BAND_GAP
  }

  // Timeless nodes fill columns top to bottom, no taller than the dated part
  // (or a square block when that is shorter), so a long list of systems does
  // not stretch the whole drawing and shrink it to fit.
  const timeless = model.nodes
    .filter((n) => TIMELESS.has(n.type))
    .sort((a, b) => order(model, a.id) - order(model, b.id) || a.label.localeCompare(b.label))
  const datedRows = Math.max(1, Math.floor((top - BAND_GAP) / ROW))
  const perColumn = Math.max(datedRows, Math.ceil(Math.sqrt(timeless.length)), 1)
  const left = Number.isFinite(maxX) ? maxX + TIMELESS_GAP : 0
  timeless.forEach((n, i) => {
    const x = left + Math.floor(i / perColumn) * TIMELESS_PITCH
    cy.getElementById(n.id).position({ x, y: (i % perColumn) * ROW + NODE / 2 })
  })
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
        border: colour,
        icon: iconDataUri(n.type, n.state ? colour : p.ink),
      },
    }
  })
  const edges = model.edges.map((e) => ({
    data: { id: `${e.source}|${e.type}|${e.target}`, source: e.source, target: e.target, type: e.type },
  }))
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
        'curve-style': 'taxi',
        'taxi-direction': 'horizontal',
        'taxi-turn': '50%',
        'line-color': p.muted,
        'target-arrow-shape': 'triangle',
        'target-arrow-color': p.muted,
        'arrow-scale': 0.7,
        label: 'data(type)',
        color: p.muted,
        'font-family': '"JetBrains Mono", ui-monospace, monospace',
        'font-size': 9,
        'text-background-color': p.base,
        'text-background-opacity': 1,
        'text-background-padding': '2px',
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
        color: p.contradicted,
      },
    },
  ]
}

function describe(model: GraphModel): string {
  const parts = model.typeCounts.map((t) => `${t.count} ${t.type}`)
  return `Traversal path: ${model.nodes.length} nodes (${parts.join(', ')}) and ${model.edges.length} edges.`
}
