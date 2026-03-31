import { useState, useEffect } from 'react'
import { apiClient } from '../api/client'

/**
 * Custom hook that fetches all metrics data in parallel.
 *
 * Sends three concurrent requests to `/api/metrics/acceptance`,
 * `/api/metrics/errors`, and `/api/metrics/quality`, then merges the results
 * into a single `metrics` object.  The fetch is automatically re-triggered
 * when `filters.language` or `filters.timePeriod` changes.  Any in-flight
 * request is aborted via `AbortController` when the component unmounts or
 * filters change, preventing stale-state updates.
 *
 * @param {{ language?: string, timePeriod?: string }} filters - Active filter values.
 * @returns {{ metrics: object|null, loading: boolean, error: string|null }}
 */
export function useMetrics(filters) {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    const controller = new AbortController()
    const { signal } = controller
    setLoading(true)
    setError(null)

    const acceptanceParams = {}
    if (filters.language) acceptanceParams.language = filters.language
    if (filters.timePeriod) acceptanceParams.time_period = filters.timePeriod

    const errorParams = {}
    if (filters.language) errorParams.language = filters.language
    if (filters.timePeriod) errorParams.time_period = filters.timePeriod

    const qualityParams = {}
    if (filters.timePeriod) qualityParams.time_period = filters.timePeriod

    Promise.all([
      apiClient.get('/api/metrics/acceptance', { params: acceptanceParams, signal }),
      apiClient.get('/api/metrics/errors', { params: errorParams, signal }),
      apiClient.get('/api/metrics/quality', { params: qualityParams, signal }),
    ])
      .then(([acceptanceRes, errorsRes, qualityRes]) => {
        setMetrics({
          acceptanceRate: acceptanceRes.data.acceptance_rate ?? 0,
          acceptanceTrend: acceptanceRes.data.trend || [],
          byLanguage: acceptanceRes.data.by_language || {},
          byInteractionType: acceptanceRes.data.by_interaction_type || {},
          errorDistribution: errorsRes.data.error_distribution || {},
          mostCommonError: errorsRes.data.most_common_error,
          avgRecoveryIterations: errorsRes.data.average_recovery_iterations ?? 0,
          recoveryRate: errorsRes.data.recovery_rate ?? 0,
          qualityMetrics: qualityRes.data.metrics || [],
          avgQualityScore: qualityRes.data.average_quality_score ?? 0,
          qualityTrend: qualityRes.data.trend || 'stable',
        })
      })
      .catch((err) => {
        if (err.name === 'CanceledError' || err.name === 'AbortError') return
        console.error('Error fetching metrics:', err)
        setError(err.response?.data?.message || err.message)
        setMetrics(null)
      })
      .finally(() => {
        if (!signal.aborted) setLoading(false)
      })

    return () => {
      controller.abort()
    }
  }, [filters.language, filters.timePeriod])

  return { metrics, loading, error }
}
