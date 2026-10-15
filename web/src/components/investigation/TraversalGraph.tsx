import { useEffect, useRef, useCallback } from 'react'
import type { ConflictClaim, GraphEdge, GraphNode, GraphPath } from '../../types'
import styles from './TraversalGraph.module.css'

// Cytoscape and dagre are imported dynamically to allow tree-shaking.
// We do it at module top level because the component always needs them.
import cytoscape from 'cytoscape'
// eslint-disable-next-line @typescript-eslint/no-require-imports
import dagre from 'cytoscape-dagre'

// Register dagre layout once
let dagreRegistered = false
function ensureDagre() {
  if (!dagreRegistered) {
    cytoscape.use(dagre)
    dagreRegistered = true
  }
}

// ── Node colour map (matches CSS design tokens) ───────────────────────────────
const NODE_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  claim:    { bg: '#1e2952', border: '#6366f1', text: '#a5b4fc' },
  document: { bg: '#172038', border: '#3b82f6', text: '#93c5fd' },
  decision: { bg: '#1e1540', border: '#8b5cf6', text: '#c4b5fd' },
  system:   { bg: '#102820', border: '#10b981', text: '#6ee7b7' },
  person:   { bg: '#2a1e0a', border: '#f59e0b', text: '#fcd34d' },
  message:  { bg: '#0d2030', border: '#06b6d4', text: '#67e8f9' },
  ticket:   { bg: '#1e0a2a', border: '#a855f7', text: '#d8b4fe' },
  entity:   { bg: '#2a1a08', border: '#f97316', text: '#fdba74' },
}

const DEFAULT_NODE = { bg: '#1a2236', border: '#475569', text: '#94a3b8' }

// ── Edge colour map ───────────────────────────────────────────────────────────
const EDGE_COLORS: Record<string, string> = {
  ASSERTS:      '#3b82f6',
  ABOUT:        '#f97316',
  CONTRADICTS:  '#ef4444',
  SUPERSEDES:   '#f59e0b',
  CITES:        '#8b5cf6',
  GOVERNS:      '#10b981',
  AUTHORED:     '#06b6d4',
  OWNS:         '#06b6d4',
  DERIVED_FROM: '#94a3b8',
  INVOLVES:     '#6366f1',
  RESOLVED_AS:  '#22c55e',
}

// ── Stylesheet ────────────────────────────────────────────────────────────────
function buildStylesheet() {
  return [
    {
      selector: 'node',
      style: {
        'shape': 'round-rectangle',
        'width': 'label',
        'height': 'label',
        'padding': '10px',
        'background-color': 'data(bg)',
        'border-color': 'data(border)',
        'border-width': 2,
        'color': 'data(textColor)',
        'font-family': 'Inter, system-ui, sans-serif',
        'font-size': '11px',
        'font-weight': '500',
        'label': 'data(label)',
        'text-valign': 'center',
        'text-halign': 'center',
        'text-wrap': 'wrap',
        'text-max-width': '140px',
        'cursor': 'pointer',
        'transition-property': 'border-color, border-width, background-color',
        'transition-duration': '150ms',
      },
    },
    {
      selector: 'node:selected',
      style: {
        'border-width': 3,
        'border-color': '#a5b4fc',
        'background-color': '#1e2952',
        'box-shadow': '0 0 12px rgba(99, 102, 241, 0.5)',
      },
    },
    {
      selector: 'node[nodeType = "claim"][state = "live"]',
      style: { 'border-color': '#10b981' },
    },
    {
      selector: 'node[nodeType = "claim"][state = "contradicted"]',
      style: { 'border-color': '#ef4444' },
    },
    {
      selector: 'node[nodeType = "claim"][state = "superseded"]',
      style: { 'border-color': '#f59e0b' },
    },
    {
      selector: 'edge',
      style: {
        'width': 2,
        'line-color': 'data(color)',
        'target-arrow-color': 'data(color)',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'arrow-scale': 0.9,
        'font-family': 'Inter, system-ui, sans-serif',
        'font-size': '9px',
        'label': 'data(label)',
        'color': '#64748b',
        'text-background-color': '#0b0f19',
        'text-background-opacity': 0.85,
        'text-background-padding': '3px',
        'text-background-shape': 'round-rectangle',
        'edge-text-rotation': 'autorotate',
        'cursor': 'pointer',
        'transition-property': 'line-color, width',
        'transition-duration': '150ms',
        'opacity': 0.85,
      },
    },
    {
      selector: 'edge:selected',
      style: {
        'width': 3,
        'opacity': 1,
      },
    },
    {
      // Highlight CONTRADICTS edges
      selector: 'edge[edgeType = "CONTRADICTS"]',
      style: {
        'width': 3,
        'line-style': 'dashed',
        'line-dash-pattern': [8, 4],
        'opacity': 1,
      },
    },
  ]
}

// ── Build Cytoscape elements from GraphPath ───────────────────────────────────
function buildElements(path: GraphPath, claims: ConflictClaim[]) {
  const claimIds = new Set(claims.map(c => c.id))

  const nodes = path.nodes.map(n => {
    const colors = NODE_COLORS[n.type] ?? DEFAULT_NODE
    return {
      data: {
        id: n.id,
        label: n.label,
        nodeType: n.type,
        state: n.state ?? '',
        bg: colors.bg,
        border: colors.border,
        textColor: colors.text,
        isClaim: claimIds.has(n.id),
      },
    }
  })

  // Deduplicate edges — backend may produce duplicate rows via OPTIONAL MATCH
  const edgeSeen = new Set<string>()
  const edges: cytoscape.ElementDefinition[] = []

  for (const e of path.edges) {
    const key = `${e.source}--${e.type}--${e.target}`
    if (edgeSeen.has(key)) continue
    // Skip edges whose endpoints aren't in the node set
    const nodeIds = new Set(path.nodes.map(n => n.id))
    if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) continue
    edgeSeen.add(key)
    edges.push({
      data: {
        id: key,
        source: e.source,
        target: e.target,
        edgeType: e.type,
        label: e.type.replace(/_/g, ' '),
        color: EDGE_COLORS[e.type] ?? '#64748b',
      },
    })
  }

  return [...nodes, ...edges]
}

// ── Component ─────────────────────────────────────────────────────────────────

interface TraversalGraphProps {
  path: GraphPath
  conflictId: string
  claims: ConflictClaim[]
  selection: { kind: string }
  onNodeSelect: (node: GraphNode) => void
  onEdgeSelect: (edge: GraphEdge) => void
  onDeselect: () => void
}

export function TraversalGraph({
  path,
  conflictId,
  claims,
  onNodeSelect,
  onEdgeSelect,
  onDeselect,
}: TraversalGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)

  // ── Initialise Cytoscape once ──────────────────────────────────────────────
  useEffect(() => {
    ensureDagre()
    if (!containerRef.current) return

    const cy = cytoscape({
      container: containerRef.current,
      elements: buildElements(path, claims),
      style: buildStylesheet() as cytoscape.StylesheetStyle[],
      layout: { name: 'preset' }, // Position later, after container has dimensions
      minZoom: 0.2,
      maxZoom: 3,
      userPanningEnabled: true,
      userZoomingEnabled: true,
      boxSelectionEnabled: false,
    })

    cy.on('tap', 'node', evt => {
      const nodeData = evt.target.data()
      onNodeSelect({
        id: nodeData.id as string,
        label: nodeData.label as string,
        type: nodeData.nodeType,
        state: nodeData.state || undefined,
      })
    })

    cy.on('tap', 'edge', evt => {
      const edgeData = evt.target.data()
      onEdgeSelect({
        source: edgeData.source as string,
        target: edgeData.target as string,
        type: edgeData.edgeType,
      })
    })

    cy.on('tap', evt => {
      if (evt.target === cy) {
        onDeselect()
        cy.elements().unselect()
      }
    })

    cyRef.current = cy

    // Run layout + fit AFTER the browser has painted and the container has real dimensions.
    // RAF handles the common case; setTimeout(100) handles slow flex resolution.
    const runLayout = () => {
      if (!cyRef.current) return
      const c = cyRef.current
      c.layout({
        name: 'dagre',
        rankDir: 'TB',
        nodeSep: 60,
        rankSep: 80,
        padding: 32,
        animate: false,
      } as cytoscape.LayoutOptions).run()
      c.resize()
      c.fit(undefined, 32)
    }

    const raf = requestAnimationFrame(runLayout)
    const timer = window.setTimeout(runLayout, 120)

    return () => {
      cancelAnimationFrame(raf)
      clearTimeout(timer)
      cy.destroy()
      cyRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conflictId]) // Only re-create on conflict change

  // ── Update elements when path changes (same conflict, fresh data) ──────────
  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return
    cy.elements().remove()
    cy.add(buildElements(path, claims))
    cy.layout({
      name: 'dagre',
      rankDir: 'TB',
      nodeSep: 60,
      rankSep: 80,
      padding: 32,
      animate: false,
    } as cytoscape.LayoutOptions).run()
    cy.resize()
    cy.fit(undefined, 32)
  }, [path, claims])

  // ── Resize observer — reflows layout when container resizes ───────────────
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let firstCall = true
    const ro = new ResizeObserver(() => {
      const cy = cyRef.current
      if (!cy) return
      cy.resize()
      // On first observed resize (initial layout), re-run layout + fit
      if (firstCall) {
        firstCall = false
        cy.layout({
          name: 'dagre',
          rankDir: 'TB',
          nodeSep: 60,
          rankSep: 80,
          padding: 32,
          animate: false,
        } as cytoscape.LayoutOptions).run()
        cy.fit(undefined, 32)
      }
    })
    ro.observe(container)
    return () => ro.disconnect()
  }, [])

  const fitGraph = useCallback(() => {
    cyRef.current?.fit(undefined, 32)
  }, [])

  const resetZoom = useCallback(() => {
    cyRef.current?.zoom(1)
    cyRef.current?.center()
  }, [])

  const zoomIn = useCallback(() => {
    const cy = cyRef.current
    if (cy) cy.zoom(Math.min(cy.zoom() * 1.3, 3))
  }, [])

  const zoomOut = useCallback(() => {
    const cy = cyRef.current
    if (cy) cy.zoom(Math.max(cy.zoom() / 1.3, 0.2))
  }, [])

  return (
    <div className={styles.wrapper}>
      {/* Toolbar */}
      <div className={styles.toolbar} role="toolbar" aria-label="Graph controls">
        <span className={styles.nodeCount} aria-live="polite">
          {path.nodes.length} nodes · {path.edges.length} edges
        </span>

        <div className={styles.controls}>
          <button className={styles.ctrlBtn} onClick={zoomIn} aria-label="Zoom in">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2" />
              <path d="M21 21l-4.35-4.35M11 8v6M8 11h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
          <button className={styles.ctrlBtn} onClick={zoomOut} aria-label="Zoom out">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2" />
              <path d="M21 21l-4.35-4.35M8 11h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
          <button className={styles.ctrlBtn} onClick={fitGraph} aria-label="Fit graph to screen">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M8 3H5a2 2 0 00-2 2v3M21 8V5a2 2 0 00-2-2h-3M3 16v3a2 2 0 002 2h3M16 21h3a2 2 0 002-2v-3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <button className={styles.ctrlBtn} onClick={resetZoom} aria-label="Reset zoom to 100%">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M1 4v6h6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M3.51 15a9 9 0 102.13-9.36L1 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className={styles.legend} aria-label="Graph legend">
        {Object.entries(NODE_COLORS).slice(0, 6).map(([type, colors]) => (
          <div key={type} className={styles.legendItem}>
            <span
              className={styles.legendDot}
              style={{ background: colors.border }}
              aria-hidden="true"
            />
            <span className={styles.legendLabel}>{type}</span>
          </div>
        ))}
        <div className={styles.legendItem}>
          <span className={styles.legendLine} style={{ background: EDGE_COLORS.CONTRADICTS }} aria-hidden="true" />
          <span className={styles.legendLabel}>CONTRADICTS</span>
        </div>
      </div>

      {/* Cytoscape container */}
      <div
        ref={containerRef}
        className={styles.canvas}
        aria-label="Interactive traversal graph — click nodes and edges to inspect"
        role="img"
      />

      {/* Empty guard */}
      {path.nodes.length === 0 && (
        <div className={styles.emptyGraph}>
          <p>No graph data for this conflict.</p>
        </div>
      )}
    </div>
  )
}
