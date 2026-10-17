import { useEffect, useRef, useState } from 'react'
import type { Workspace } from '../../types'
import type { Async } from '../../lib/useAsync'
import { navigate } from '../../lib/router'
import { count } from '../../lib/format'
import { Icon } from '../Icon'
import styles from './WorkspaceSwitcher.module.css'

interface Props {
  currentId: string
  workspaces: Async<Workspace[]>
  onSwitch: (id: string) => void
}

/** The current workspace's name; opens a flat panel listing every workspace. */
export function WorkspaceSwitcher({ currentId, workspaces, onSwitch }: Props) {
  const [open, setOpen] = useState(false)
  const [anchor, setAnchor] = useState<{ top: number; left: number } | null>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)

  const list = workspaces.status === 'ready' ? workspaces.data : null
  const current = list?.find((w) => w.id === currentId) ?? null

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false)
        buttonRef.current?.focus()
      }
    }
    const onDown = (e: MouseEvent) => {
      const t = e.target as Node
      if (!panelRef.current?.contains(t) && !buttonRef.current?.contains(t)) setOpen(false)
    }
    window.addEventListener('keydown', onKey)
    window.addEventListener('mousedown', onDown)
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('mousedown', onDown)
    }
  }, [open])

  const toggle = () => {
    const r = buttonRef.current?.getBoundingClientRect()
    if (r) setAnchor({ top: r.bottom + 4, left: r.left + 12 })
    setOpen((o) => !o)
  }

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        className={styles.current}
        aria-haspopup="true"
        aria-expanded={open}
        onClick={toggle}
        title={current ? `${current.name} · ${current.graph}` : currentId}
      >
        {current ? (
          <span className={styles.name}>{current.name}</span>
        ) : (
          <span className={styles.id}>{currentId}</span>
        )}
        <Icon name="chevron-down" size={16} className={styles.chevron} />
      </button>

      {open && anchor ? (
        <div
          ref={panelRef}
          className={styles.panel}
          style={{ top: anchor.top, left: anchor.left }}
          role="dialog"
          aria-label="Workspaces"
        >
          <p className={`cap ${styles.panelHead}`}>Workspaces</p>
          {workspaces.status === 'error' ? (
            <p className={styles.error}>
              The workspace list did not load. <code>{workspaces.error}</code>
            </p>
          ) : list ? (
            <ul className={styles.list}>
              {list.map((w) => (
                <li key={w.id}>
                  <button
                    type="button"
                    className={styles.item}
                    aria-current={w.id === currentId ? 'true' : undefined}
                    onClick={() => {
                      setOpen(false)
                      if (w.id !== currentId) onSwitch(w.id)
                    }}
                  >
                    <span className={styles.itemName}>{w.name}</span>
                    <span className={styles.itemMeta}>
                      {count(w.documents)} docs · {count(w.conflicts)} open
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className={styles.error}>Loading workspaces.</p>
          )}
          <button
            type="button"
            className={`btn ${styles.new}`}
            onClick={() => {
              setOpen(false)
              navigate({ name: 'setup', workspace: null })
            }}
          >
            New workspace
          </button>
        </div>
      ) : null}
    </>
  )
}
