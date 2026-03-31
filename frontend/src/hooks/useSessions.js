import { useState, useEffect } from 'react'
import { apiClient } from '../api/client'

/**
 * Custom hook that fetches a paginated, filtered list of sessions.
 *
 * Sends a request to `/api/sessions` whenever any of the filter values
 * change.  The in-flight request is cancelled via `AbortController` on
 * cleanup to prevent stale state updates.
 *
 * @param {{
 *   language?: string,
 *   status?: string,
 *   startDate?: string,
 *   endDate?: string,
 *   limit?: number,
 *   offset?: number
 * }} filters - Query parameters forwarded to the API.
 * @returns {{ sessions: object[], totalCount: number, loading: boolean, error: string|null }}
 */
export function useSessions(filters) {
  const [sessions, setSessions] = useState([])
  const [totalCount, setTotalCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(null)

    const params = {}
    if (filters.language) params.language = filters.language
    if (filters.status && filters.status !== 'all') params.status = filters.status
    if (filters.startDate) params.start_date = filters.startDate
    if (filters.endDate) params.end_date = filters.endDate
    if (filters.limit) params.limit = filters.limit
    if (filters.offset) params.offset = filters.offset

    apiClient
      .get('/api/sessions', { params, signal: controller.signal })
      .then((response) => {
        setSessions(response.data.sessions || [])
        setTotalCount(response.data.total_count || 0)
      })
      .catch((err) => {
        if (err.name === 'CanceledError' || err.name === 'AbortError') return
        console.error('Error fetching sessions:', err)
        setError(err.response?.data?.message || err.message)
        setSessions([])
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })

    return () => {
      controller.abort()
    }
  }, [
    filters.language,
    filters.status,
    filters.startDate,
    filters.endDate,
    filters.limit,
    filters.offset,
  ])

  return { sessions, totalCount, loading, error }
}
