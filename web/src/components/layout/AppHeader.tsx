import styles from './AppHeader.module.css'

interface AppHeaderProps {
  conflictCount: number | null
}

export function AppHeader({ conflictCount }: AppHeaderProps) {
  return (
    <header className={styles.header} role="banner">
      <div className={styles.inner}>
        <div className={styles.brand}>
          {/* Wordmark */}
          <svg
            className={styles.logo}
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M12 2L2 7l10 5 10-5-10-5z"
              fill="currentColor"
              opacity="0.9"
            />
            <path
              d="M2 17l10 5 10-5"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity="0.6"
            />
            <path
              d="M2 12l10 5 10-5"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className={styles.wordmark}>Faultline</span>
        </div>

        <nav className={styles.nav} aria-label="Main navigation">
          <span className={styles.tagline}>
            Organisational knowledge contradiction detection
          </span>
        </nav>

        {conflictCount !== null && (
          <div className={styles.badge} aria-label={`${conflictCount} open conflicts`}>
            <span className={styles.badgeDot} aria-hidden="true" />
            <span>{conflictCount} open</span>
          </div>
        )}
      </div>
    </header>
  )
}
