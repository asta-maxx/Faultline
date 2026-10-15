import type { ConflictStatusFilter, ConflictSortField } from '../../types'
import styles from './QueueFilters.module.css'

interface QueueFiltersProps {
  status: ConflictStatusFilter
  sortBy: ConflictSortField
  onStatusChange: (status: ConflictStatusFilter) => void
  onSortChange: (sort: ConflictSortField) => void
}

const STATUS_OPTIONS: { value: ConflictStatusFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'open', label: 'Open' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'dismissed', label: 'Dismissed' },
]

const SORT_OPTIONS: { value: ConflictSortField; label: string }[] = [
  { value: 'blast_radius', label: 'Blast radius' },
  { value: 'found_at', label: 'Discovery time' },
]

export function QueueFilters({
  status,
  sortBy,
  onStatusChange,
  onSortChange,
}: QueueFiltersProps) {
  return (
    <div className={styles.filters} role="toolbar" aria-label="Filter and sort conflicts">
      {/* Status pills */}
      <div className={styles.group} role="group" aria-label="Filter by status">
        {STATUS_OPTIONS.map(opt => (
          <button
            key={opt.value}
            className={`${styles.pill} ${status === opt.value ? styles.pillActive : ''}`}
            onClick={() => onStatusChange(opt.value)}
            aria-pressed={status === opt.value}
            aria-label={`Show ${opt.label} conflicts`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Sort select */}
      <div className={styles.sortGroup}>
        <label htmlFor="conflict-sort" className={styles.sortLabel}>
          Sort by
        </label>
        <select
          id="conflict-sort"
          className={styles.sortSelect}
          value={sortBy}
          onChange={e => onSortChange(e.target.value as ConflictSortField)}
          aria-label="Sort conflicts by"
        >
          {SORT_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
