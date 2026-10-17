import { useEffect, useState } from 'react'

/**
 * Five routes: /conflicts[/:id], /resolved, /sources, /setup and /audit/:run_id.
 * A router library would be the larger part of this file, so history is
 * handled directly.
 *
 * /setup with no query starts a new workspace; /setup?workspace=<id> adds
 * sources to an existing one (the setup screen moves itself there once it has
 * created the workspace, so a reload keeps it).
 */
export type Route =
  | { name: 'conflicts'; conflictId: string | null }
  | { name: 'resolved' }
  | { name: 'sources' }
  | { name: 'setup'; workspace: string | null }
  | { name: 'audit'; runId: string }

export function parseRoute(pathname: string, search = ''): Route {
  const parts = pathname.split('/').filter(Boolean)
  if (parts[0] === 'resolved') return { name: 'resolved' }
  if (parts[0] === 'sources') return { name: 'sources' }
  if (parts[0] === 'setup') return { name: 'setup', workspace: new URLSearchParams(search).get('workspace') }
  if (parts[0] === 'audit' && parts[1]) return { name: 'audit', runId: decodeURIComponent(parts[1]) }
  return { name: 'conflicts', conflictId: parts[0] === 'conflicts' && parts[1] ? decodeURIComponent(parts[1]) : null }
}

export function routePath(route: Route): string {
  switch (route.name) {
    case 'resolved':
      return '/resolved'
    case 'sources':
      return '/sources'
    case 'setup':
      return route.workspace ? `/setup?workspace=${encodeURIComponent(route.workspace)}` : '/setup'
    case 'audit':
      return `/audit/${encodeURIComponent(route.runId)}`
    case 'conflicts':
      return route.conflictId ? `/conflicts/${encodeURIComponent(route.conflictId)}` : '/conflicts'
  }
}

const listeners = new Set<() => void>()

export function navigate(route: Route, replace = false): void {
  const path = routePath(route)
  // Only /setup carries meaning in its query; elsewhere the query (?node=) is view state and stays.
  const here = route.name === 'setup' ? window.location.pathname + window.location.search : window.location.pathname
  if (path === here) return
  if (replace) window.history.replaceState(null, '', path)
  else window.history.pushState(null, '', path)
  listeners.forEach((fn) => fn())
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseRoute(window.location.pathname, window.location.search))
  useEffect(() => {
    const update = () => setRoute(parseRoute(window.location.pathname, window.location.search))
    listeners.add(update)
    window.addEventListener('popstate', update)
    return () => {
      listeners.delete(update)
      window.removeEventListener('popstate', update)
    }
  }, [])
  return route
}
