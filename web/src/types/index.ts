/**
 * Faultline frontend types — CONTRACT.md §5 and §9 (frozen).
 * Field names match the API response exactly. Nothing here is optional
 * unless the contract makes it optional.
 */

export type ClaimState = 'live' | 'contradicted' | 'superseded'
export type ConflictKind = 'direct' | 'superseded' | 'undocumented'
export type ConflictStatus = 'open' | 'resolved' | 'dismissed'

export interface ClaimSource {
  doc_id: string
  title: string
  path: string
  updated_at: number // epoch seconds
}

export interface ConflictClaim {
  side: 'a' | 'b'
  id: string
  text: string
  confidence: number
  evidence_span: string
  state: ClaimState
  source: ClaimSource
}

export interface Person {
  id: string
  name: string
  role: string
}

export interface Conflict {
  id: string
  kind: ConflictKind
  status: ConflictStatus
  blast_radius: number
  found_at: number // epoch seconds
  entity: { id: string; name: string; type: string }
  claims: ConflictClaim[]
  impact: { doc_count: number; system_count: number; systems: string[] }
  owner: Person | null
  /** v5, optional: the CONTRADICTS edge between the two claims. */
  judgement?: Judgement | null
  /** v5, optional: the RESOLVED_AS edge; null unless status is "resolved". */
  resolution?: Resolution | null
}

export interface Judgement {
  method: string
  confidence: number
  evidence_span: string
}

export interface Resolution {
  winner_claim_id: string
  rationale: string
  resolved_at: number
  resolved_by: string
}

/** `type` is the §5 node label lowercased. */
export type NodeType =
  | 'claim'
  | 'entity'
  | 'document'
  | 'decision'
  | 'person'
  | 'system'
  | 'ticket'
  | 'message'
  | 'conflict'

/** §5 edge types. No other edge names exist. */
export type EdgeType =
  | 'ASSERTS'
  | 'ABOUT'
  | 'CONTRADICTS'
  | 'SUPERSEDES'
  | 'CITES'
  | 'GOVERNS'
  | 'AUTHORED'
  | 'OWNS'
  | 'DERIVED_FROM'
  | 'INVOLVES'
  | 'RESOLVED_AS'

export interface GraphNode {
  id: string
  label: string
  type: NodeType
  state?: ClaimState
  /** v5, optional: the node's own §5 date, epoch seconds; a claim takes its source's. */
  at?: number
}

export interface GraphEdge {
  source: string
  target: string
  type: EdgeType
}

export interface GraphPath {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface Stats {
  claims: number
  documents: number
  entities: number
  naive_pair_count: number
  collapsed_pair_count: number
  prefiltered_pair_count: number
  judged_pair_count: number
  conflicts_open: number
  conflicts_resolved: number
}

export interface HealthResponse {
  ok: boolean
  graph: string
  nodes: number
  edges: number
  falkor: 'up' | 'down'
}

export interface ConflictsResponse {
  conflicts: Conflict[]
  total: number
  stats: Stats
}

export interface ConflictDetailResponse {
  conflict: Conflict
  path: GraphPath
}

export interface ResolveRequest {
  winner_claim_id: string
  rationale: string
  resolved_by: string
}

export interface ResolveResponse {
  ok: true
  conflict: Conflict
}

export interface DraftResponse {
  correction: string
  owner: Person
  ticket: { title: string; body: string }
}

export interface ReingestResponse {
  job_id: string
}

// ── CONTRACT §9b: workspaces, sources and audits (v6) ─────────────────────────

export interface Workspace {
  id: string
  name: string
  /** "faultline:{id}" */
  graph: string
  sources: number
  documents: number
  claims: number
  /** open conflicts */
  conflicts: number
  /** epoch seconds, end of the latest finished audit */
  last_audit: number | null
  /** the most recent audit of any status; open /audit/{run_id} for it */
  latest_run: LatestRun | null
}

export interface LatestRun {
  run_id: string
  status: 'running' | 'done' | 'failed'
  started_at: number
}

export type SourceKind = 'folder' | 'git'
export type SourceStatus = 'ready' | 'unsupported' | 'missing'

export interface Source {
  id: string
  kind: SourceKind
  location: string
  /** readable files found when scanned; null if never scanned */
  docs: number | null
  /** claims extracted from it by the latest audit */
  claims: number | null
  status: SourceStatus
  /** plain-language reason for any status other than "ready" */
  message: string | null
  /** a token was supplied; the token itself is never stored */
  has_token: boolean
  added_at: number
  last_read_at: number | null
}

export interface AddSourceRequest {
  kind: SourceKind
  location: string
  token?: string
}

export type AuditStageName =
  | 'READING SOURCES'
  | 'EXTRACTING CLAIMS'
  | 'BUILDING GRAPH'
  | 'COLLAPSING CANDIDATES'
  | 'JUDGING PAIRS'

export type AuditStageState = 'pending' | 'active' | 'done' | 'failed'

export interface AuditStage {
  name: AuditStageName
  state: AuditStageState
  count: number | null
  unit: string
  detail: string | null
  started_at: number | null
  ended_at: number | null
}

export interface AuditSummary {
  documents: number
  claims: number
  pairs_compared: number
  judged: number
  contradictions: number
}

export interface AuditRun {
  run_id: string
  workspace_id: string
  status: 'running' | 'done' | 'failed'
  stage: string | null
  stages: AuditStage[]
  current: string | null
  summary: AuditSummary | null
  error: string | null
  started_at: number
  ended_at: number | null
}

export interface StartAuditResponse {
  run_id: string
}
