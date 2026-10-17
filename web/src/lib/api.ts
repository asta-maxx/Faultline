/**
 * Faultline API client — one function per endpoint in CONTRACT §9 and §9b.
 *
 * This is the only file that knows where data comes from, and the one place
 * that holds the current workspace. Every §9 conflict and stats call carries
 * `?workspace=<id>`; the id survives reloads in localStorage, and a
 * `?workspace=<id>` in the page URL selects a workspace on load so a view
 * of one workspace can be shared.
 */

import { useSyncExternalStore } from 'react'
import type {
  AddSourceRequest,
  AuditRun,
  ConflictDetailResponse,
  ConflictsResponse,
  ConflictStatus,
  DismissRequest,
  DismissResponse,
  DraftResponse,
  HealthResponse,
  ReingestResponse,
  ResolveRequest,
  ResolveResponse,
  Source,
  StartAuditResponse,
  Stats,
  Workspace,
} from '../types'

const API_BASE = '/api'

/** The workspace the API serves when none is named (CONTRACT §9b). */
export const DEFAULT_WORKSPACE = 'northwind'

// ── Errors ───────────────────────────────────────────────────────────────────

/** A non-2xx answer. `detail` is the server's own message, verbatim. */
export class ApiError extends Error {
  readonly status: number
  readonly detail: string

  constructor(method: string, url: string, status: number, detail: string) {
    super(`${method} ${url} returned ${status}: ${detail}`)
    this.status = status
    this.detail = detail
  }
}

/** FastAPI puts its message in `detail`: a string, or a list of validation errors. */
function readDetail(text: string): string {
  try {
    const body: unknown = JSON.parse(text)
    if (body && typeof body === 'object' && 'detail' in body) {
      const detail = (body as { detail: unknown }).detail
      if (typeof detail === 'string') return detail
      if (Array.isArray(detail)) {
        return detail
          .map((d) => (d && typeof d === 'object' && 'msg' in d ? String((d as { msg: unknown }).msg) : JSON.stringify(d)))
          .join('; ')
      }
      return JSON.stringify(detail)
    }
  } catch {
    // Not JSON: the text is the message.
  }
  return text
}

/** What to print inline for a failed call: the status and the server's words, unedited. */
export function errorText(err: unknown): string {
  if (err instanceof ApiError) return `${err.status} · ${err.detail}`
  return err instanceof Error ? err.message : String(err)
}

async function request<T>(method: 'GET' | 'POST' | 'DELETE', path: string, init: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`
  const res = await fetch(url, {
    method,
    ...init,
    headers: { Accept: 'application/json', ...init.headers },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new ApiError(method, url, res.status, readDetail(text) || res.statusText)
  }
  return res.json() as Promise<T>
}

function postJson<T>(path: string, body: unknown, headers: Record<string, string> = {}): Promise<T> {
  return request<T>('POST', path, {
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json', ...headers },
  })
}

// ── Current workspace ────────────────────────────────────────────────────────

const WORKSPACE_KEY = 'faultline.workspace'

export function readStorage(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

export function writeStorage(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    // Storage blocked: the choice lasts until reload.
  }
}

function initialWorkspace(): string {
  const fromUrl = new URLSearchParams(window.location.search).get('workspace')
  if (fromUrl) {
    writeStorage(WORKSPACE_KEY, fromUrl)
    return fromUrl
  }
  return readStorage(WORKSPACE_KEY) || DEFAULT_WORKSPACE
}

let workspaceId = initialWorkspace()
/** Bumped on every switch and whenever a workspace's data is known to have changed. */
let epoch = 0
const workspaceListeners = new Set<() => void>()

export function currentWorkspaceId(): string {
  return workspaceId
}

/** Switch workspace. Everything keyed on `useWorkspace().key` reloads. */
export function setWorkspace(id: string): void {
  workspaceId = id
  writeStorage(WORKSPACE_KEY, id)
  epoch += 1
  workspaceListeners.forEach((fn) => fn())
}

/** The current workspace's records or graph changed: reload what was loaded for it. */
export function refreshWorkspaceData(): void {
  epoch += 1
  workspaceListeners.forEach((fn) => fn())
}

function subscribeWorkspace(fn: () => void): () => void {
  workspaceListeners.add(fn)
  return () => {
    workspaceListeners.delete(fn)
  }
}

function workspaceSnapshot(): string {
  return `${workspaceId}#${epoch}`
}

/** `{id, key}`: `key` changes on every switch or refresh, so it is the load key. */
export function useWorkspace(): { id: string; key: string } {
  const key = useSyncExternalStore(subscribeWorkspace, workspaceSnapshot)
  return { id: key.slice(0, key.lastIndexOf('#')), key }
}

/** Append `workspace=<current>` to a §9 path. */
function scoped(path: string): string {
  return `${path}${path.includes('?') ? '&' : '?'}workspace=${encodeURIComponent(workspaceId)}`
}

// ── §9 ───────────────────────────────────────────────────────────────────────

/** GET /health — 503 is a valid answer (FalkorDB down) and still carries the body. */
export async function getHealth(): Promise<HealthResponse> {
  const url = `${API_BASE}/health`
  const res = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!res.ok && res.status !== 503) {
    throw new Error(`GET ${url} returned ${res.status}: ${await res.text().catch(() => res.statusText)}`)
  }
  return res.json() as Promise<HealthResponse>
}

/** GET /conflicts?status=&limit=&workspace= */
export function listConflicts(status: ConflictStatus, limit = 200): Promise<ConflictsResponse> {
  const params = new URLSearchParams({ status, limit: String(limit) })
  return request('GET', scoped(`/conflicts?${params}`))
}

/** GET /conflicts/{id}?workspace= */
export function getConflict(id: string): Promise<ConflictDetailResponse> {
  return request('GET', scoped(`/conflicts/${encodeURIComponent(id)}`))
}

/** POST /conflicts/{id}/resolve?workspace= */
export function resolveConflict(id: string, body: ResolveRequest): Promise<ResolveResponse> {
  return postJson(scoped(`/conflicts/${encodeURIComponent(id)}/resolve`), body)
}

/** POST /conflicts/{id}/draft?workspace= */
export function draftCorrection(id: string): Promise<DraftResponse> {
  return postJson(scoped(`/conflicts/${encodeURIComponent(id)}/draft`), {})
}

/** POST /conflicts/{id}/dismiss?workspace= — 409 if not open, 422 if a field is empty (v7). */
export function dismissConflict(id: string, body: DismissRequest): Promise<DismissResponse> {
  return postJson(scoped(`/conflicts/${encodeURIComponent(id)}/dismiss`), body)
}

/** GET /stats?workspace= */
export function getStats(): Promise<Stats> {
  return request('GET', scoped('/stats'))
}

/** POST /reingest — token-gated, never on the demo path. */
export function reingest(token: string): Promise<ReingestResponse> {
  return postJson('/reingest', {}, { 'X-Reingest-Token': token })
}

// ── §9b ──────────────────────────────────────────────────────────────────────

/** GET /workspaces */
export function listWorkspaces(): Promise<Workspace[]> {
  return request('GET', '/workspaces')
}

/** POST /workspaces {name} — 409 if the id exists. */
export function createWorkspace(name: string): Promise<Workspace> {
  return postJson('/workspaces', { name })
}

/** GET /workspaces/{id}/sources */
export function listSources(workspace: string): Promise<Source[]> {
  return request('GET', `/workspaces/${encodeURIComponent(workspace)}/sources`)
}

/** POST /workspaces/{id}/sources — 422 if a folder is missing or outside the allowed root. */
export function addSource(workspace: string, body: AddSourceRequest): Promise<Source> {
  return postJson(`/workspaces/${encodeURIComponent(workspace)}/sources`, body)
}

/** DELETE /workspaces/{id}/sources/{source_id} */
export function removeSource(workspace: string, sourceId: string): Promise<{ ok: true }> {
  return request('DELETE', `/workspaces/${encodeURIComponent(workspace)}/sources/${encodeURIComponent(sourceId)}`)
}

/** POST /workspaces/{id}/audit — 409 if an audit is running, 422 if no readable source. */
export function startAudit(workspace: string): Promise<StartAuditResponse> {
  return postJson(`/workspaces/${encodeURIComponent(workspace)}/audit`, {})
}

/** GET /audits/{run_id} */
export function getAudit(runId: string): Promise<AuditRun> {
  return request('GET', `/audits/${encodeURIComponent(runId)}`)
}
