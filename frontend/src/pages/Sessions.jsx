import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useSessions } from '../hooks/useSessions'

const EMPTY_FILTERS = {}

function Sessions() {
  const [sortBy, setSortBy] = useState('start_time')
  const [sortOrder, setSortOrder] = useState('desc')

  const { sessions, loading, error } = useSessions(EMPTY_FILTERS)

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortOrder('asc')
    }
  }

  const sortedSessions = [...sessions].sort((a, b) => {
    const aVal = a[sortBy]
    const bVal = b[sortBy]

    if (aVal == null && bVal == null) return 0
    if (aVal == null) return 1
    if (bVal == null) return -1

    if (typeof aVal === 'string') {
      return sortOrder === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal)
    }
    return sortOrder === 'asc' ? aVal - bVal : bVal - aVal
  })

  const formatDuration = (seconds) => {
    if (seconds == null) return '-'
    if (seconds < 60) return `${seconds}s`
    return `${(seconds / 60).toFixed(1)} min`
  }

  const formatRate = (rate) => {
    if (rate == null) return '-'
    return `${(rate * 100).toFixed(1)}%`
  }

  const SortIcon = ({ column }) => {
    if (sortBy !== column) return null
    return <span className="sort-icon">{sortOrder === 'asc' ? ' \u2191' : ' \u2193'}</span>
  }

  if (loading) {
    return <div className="loading-state">Loading sessions...</div>
  }

  if (error) {
    return <div className="error-state">Error loading sessions: {error}</div>
  }

  return (
    <div className="sessions-page">
      <h2>All Sessions</h2>

      {sessions.length === 0 ? (
        <div className="empty-state">
          <p>No sessions found. Start coding with Claude Code to see data here.</p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table className="sessions-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('start_time')}>
                  Start Time
                  <SortIcon column="start_time" />
                </th>
                <th onClick={() => handleSort('duration_seconds')}>
                  Duration
                  <SortIcon column="duration_seconds" />
                </th>
                <th onClick={() => handleSort('language')}>
                  Language
                  <SortIcon column="language" />
                </th>
                <th onClick={() => handleSort('interaction_count')}>
                  Interactions
                  <SortIcon column="interaction_count" />
                </th>
                <th onClick={() => handleSort('acceptance_rate')}>
                  Acceptance
                  <SortIcon column="acceptance_rate" />
                </th>
                <th onClick={() => handleSort('status')}>
                  Status
                  <SortIcon column="status" />
                </th>
                <th>Errors</th>
              </tr>
            </thead>
            <tbody>
              {sortedSessions.map((session) => (
                <tr key={session.id} className="session-row">
                  <td>
                    <Link to={`/sessions/${session.id}`}>
                      {new Date(session.start_time).toLocaleString()}
                    </Link>
                  </td>
                  <td>{formatDuration(session.duration_seconds)}</td>
                  <td>
                    <span className="badge">{session.language}</span>
                  </td>
                  <td>{session.interaction_count ?? 0}</td>
                  <td>{formatRate(session.acceptance_rate)}</td>
                  <td>
                    <span className={`status status-${session.status}`}>{session.status}</span>
                  </td>
                  <td>{session.error_count ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default Sessions
