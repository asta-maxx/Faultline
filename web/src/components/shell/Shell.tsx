import type { ReactNode } from 'react'
// Bundled into /assets so the API's static mount serves it in production.
import logoUrl from '../../assets/faultline.svg'
import type { ConflictKind, ConflictsResponse, HealthResponse, Stats, Workspace } from '../../types'
import { navigate, type Route } from '../../lib/router'
import type { Async } from '../../lib/useAsync'
import { capitalize, count } from '../../lib/format'
import { Icon } from '../Icon'
import { WorkspaceSwitcher } from './WorkspaceSwitcher'
import styles from './Shell.module.css'

interface ShellProps {
  route: Route
  stats: Async<Stats>
  open: Async<ConflictsResponse>
  health: Async<HealthResponse>
  workspaceId: string
  workspaces: Async<Workspace[]>
  onSwitchWorkspace: (id: string) => void
  children: ReactNode
}

const KINDS: ConflictKind[] = ['direct', 'superseded', 'undocumented']

export function Shell(props: ShellProps) {
  const { route, stats, open, health, workspaceId, workspaces, onSwitchWorkspace, children } = props
  const s = stats.status === 'ready' ? stats.data : null
  const conflicts = open.status === 'ready' ? open.data.conflicts : null
  const workspace = workspaces.status === 'ready' ? (workspaces.data.find((w) => w.id === workspaceId) ?? null) : null

  return (
    <div className={styles.app}>
      <aside className={styles.rail}>
        <div className={styles.top}>
          <a
            className={styles.brand}
            href="/conflicts"
            onClick={(e) => {
              e.preventDefault()
              navigate({ name: 'conflicts', conflictId: null })
            }}
          >
            <img src={logoUrl} width={32} height={32} alt="" />
            <span>Faultline</span>
          </a>
          <WorkspaceSwitcher currentId={workspaceId} workspaces={workspaces} onSwitch={onSwitchWorkspace} />
        </div>

        <nav className={styles.nav} aria-label="Screens">
          <RailLink
            active={route.name === 'conflicts'}
            icon="conflicts"
            label="Conflicts"
            value={s?.conflicts_open}
            onClick={() => navigate({ name: 'conflicts', conflictId: null })}
          />
          <RailLink
            active={route.name === 'resolved'}
            icon="resolved"
            label="Resolved"
            value={s?.conflicts_resolved}
            onClick={() => navigate({ name: 'resolved' })}
          />
          <RailLink
            active={route.name === 'sources'}
            icon="sources"
            label="Sources"
            value={workspace?.sources}
            onClick={() => navigate({ name: 'sources' })}
          />
        </nav>

        <a
          className={styles.newWorkspace}
          href="/setup"
          aria-current={route.name === 'setup' && route.workspace === null ? 'page' : undefined}
          onClick={(e) => {
            e.preventDefault()
            navigate({ name: 'setup', workspace: null })
          }}
        >
          <Icon name="plus" size={16} />
          <span>New workspace</span>
        </a>

        <section className={styles.group} aria-label="Corpus">
          <h2 className="cap">Corpus</h2>
          <dl>
            <Row label="Documents" value={s?.documents} />
            <Row label="Entities" value={s?.entities} />
            <Row label="Claims" value={s?.claims} />
          </dl>
        </section>

        <section className={styles.group} aria-label="Open conflicts by kind">
          <h2 className="cap">By kind</h2>
          <dl>
            {KINDS.map((kind) => (
              <Row key={kind} label={capitalize(kind)} value={conflicts?.filter((c) => c.kind === kind).length} />
            ))}
          </dl>
        </section>
      </aside>

      <header className={styles.strip}>
        {s ? (
          <p className="cap">
            <span>{count(s.conflicts_open)} open</span>
            <span className="dot">{count(s.conflicts_resolved)} resolved</span>
            <span className="dot">{count(s.claims)} claims</span>
            <span className="dot">{count(s.documents)} docs</span>
            <span className="dot">{count(s.entities)} entities</span>
          </p>
        ) : (
          <p className="cap">{stats.status === 'error' ? `Stats unavailable. ${stats.error}` : ''}</p>
        )}
        <HealthMark health={health} graph={workspace?.graph ?? null} />
      </header>

      <main className={styles.main}>{children}</main>

      <footer className={styles.funnel} aria-label="Pair funnel">
        {s ? (
          <p className="cap">
            <span>
              All pairs <b className="num">{count(s.naive_pair_count)}</b>
            </span>
            <span className="dot">
              Graph collapse <b className="num">{count(s.collapsed_pair_count)}</b>
            </span>
            <span className="dot">
              Prefilter <b className="num">{count(s.prefiltered_pair_count)}</b>
            </span>
            <span className="dot">
              Judged <b className="num">{count(s.judged_pair_count)}</b>
            </span>
          </p>
        ) : null}
      </footer>
    </div>
  )
}

function RailLink(props: {
  active: boolean
  icon: 'conflicts' | 'resolved' | 'sources'
  label: string
  value: number | undefined
  onClick: () => void
}) {
  return (
    <button
      type="button"
      className={styles.navItem}
      aria-current={props.active ? 'page' : undefined}
      onClick={props.onClick}
    >
      <Icon name={props.icon} size={20} />
      <span>{props.label}</span>
      <span className={styles.navCount}>{props.value === undefined ? '' : count(props.value)}</span>
    </button>
  )
}

function Row({ label, value }: { label: string; value: number | undefined }) {
  return (
    <div className={styles.row}>
      <dt>{label}</dt>
      <dd className="num">{value === undefined ? '' : count(value)}</dd>
    </div>
  )
}

/**
 * FalkorDB reachability. /health reports one graph (the API's default); the
 * strip names the current workspace's graph instead, from its §9b record.
 */
function HealthMark({ health, graph }: { health: Async<HealthResponse>; graph: string | null }) {
  if (health.status === 'loading') return null
  if (health.status === 'error') {
    return (
      <p className={`cap ${styles.health}`} data-up="false">
        graph unreachable
      </p>
    )
  }
  const h = health.data
  return (
    <p className={`cap ${styles.health}`} data-up={h.falkor === 'up'}>
      {graph ? <span>{graph}</span> : null}
      <span className={graph ? 'dot' : undefined}>falkor {h.falkor}</span>
    </p>
  )
}
