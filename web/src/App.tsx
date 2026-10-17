import { useEffect } from 'react'
import { getHealth, getStats, listConflicts, listWorkspaces, setWorkspace, useWorkspace } from './lib/api'
import { navigate, useRoute, type Route } from './lib/router'
import { useAsync } from './lib/useAsync'
import { Shell } from './components/shell/Shell'
import { ConflictsScreen } from './components/conflicts/ConflictsScreen'
import { ResolvedScreen } from './components/resolved/ResolvedScreen'
import { SourcesScreen } from './components/sources/SourcesScreen'
import { SetupScreen } from './components/setup/SetupScreen'
import { AuditScreen } from './components/audit/AuditScreen'

export default function App() {
  const route = useRoute()
  // Every per-workspace load is keyed on ws.key, so a switch or refresh reloads it.
  const ws = useWorkspace()
  const stats = useAsync(getStats, `stats:${ws.key}`)
  const open = useAsync(() => listConflicts('open'), `open:${ws.key}`)
  const workspaces = useAsync(listWorkspaces, `workspaces:${ws.key}`)
  // Health only feeds the strip and the "N of M nodes" caption; a failure is shown, not fatal.
  const health = useAsync(getHealth, 'health')

  useEffect(() => {
    if (window.location.pathname === '/') navigate({ name: 'conflicts', conflictId: null }, true)
  }, [])

  const switchWorkspace = (id: string) => {
    setWorkspace(id)
    // A conflict id, an audit run or a setup form belongs to the old workspace.
    if (route.name === 'conflicts' || route.name === 'audit' || route.name === 'setup') {
      navigate({ name: 'conflicts', conflictId: null })
    }
  }

  return (
    <Shell
      route={route}
      stats={stats}
      open={open}
      health={health}
      workspaceId={ws.id}
      workspaces={workspaces}
      onSwitchWorkspace={switchWorkspace}
    >
      <Screen route={route} open={open} health={health} workspaceKey={ws.key} />
    </Shell>
  )
}

function Screen({
  route,
  open,
  health,
  workspaceKey,
}: {
  route: Route
  open: Parameters<typeof ConflictsScreen>[0]['open']
  health: Parameters<typeof ConflictsScreen>[0]['health']
  workspaceKey: string
}) {
  switch (route.name) {
    case 'resolved':
      return <ResolvedScreen />
    case 'sources':
      return <SourcesScreen key={workspaceKey} />
    case 'setup':
      // One instance across "create workspace, then add sources", so the form keeps what the API just said.
      return <SetupScreen key="setup" workspaceId={route.workspace} />
    case 'audit':
      return <AuditScreen key={route.runId} runId={route.runId} />
    case 'conflicts':
      return <ConflictsScreen open={open} selectedId={route.conflictId} health={health} />
  }
}
