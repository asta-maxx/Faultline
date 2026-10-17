import { useEffect, useState } from 'react'

export type Async<T> =
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ready'; data: T }

/** Runs `load` whenever `key` changes. Stale responses are discarded. */
export function useAsync<T>(load: () => Promise<T>, key: string): Async<T> {
  const [state, setState] = useState<{ key: string; value: Async<T> }>({ key, value: { status: 'loading' } })

  useEffect(() => {
    let cancelled = false
    load().then(
      (data) => !cancelled && setState({ key, value: { status: 'ready', data } }),
      (err: unknown) =>
        !cancelled && setState({ key, value: { status: 'error', error: err instanceof Error ? err.message : String(err) } }),
    )
    return () => {
      cancelled = true
    }
    // `load` is re-created every render; `key` is what identifies the request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  return state.key === key ? state.value : { status: 'loading' }
}
