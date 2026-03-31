import { useState, useMemo } from 'react'
import { BarChart3, MessageSquare, ThumbsUp, Code } from 'lucide-react'
import LanguageFilter from '../components/Filters/LanguageFilter'
import Timeline from '../components/Charts/Timeline'
import ErrorDistribution from '../components/Charts/ErrorDistribution'
import ScatterPlot from '../components/Charts/ScatterPlot'
import InsightsPanel from '../components/InsightsPanel'
import { useSessions } from '../hooks/useSessions'
import { useMetrics } from '../hooks/useMetrics'

/** Available time-range options shown as filter buttons. */
const TIME_RANGES = [
  { label: 'All Time', value: 'all_time', days: null },
  { label: 'Last 30 Days', value: 'last_30_days', days: 30 },
  { label: 'Last 60 Days', value: 'last_60_days', days: 60 },
  { label: 'Last 90 Days', value: 'last_90_days', days: 90 },
]

/**
 * Return an ISO timestamp for *days* ago, or null when *days* is falsy.
 * Used to derive the `startDate` filter value from a time-range selection.
 *
 * @param {number|null} days
 * @returns {string|null}
 */
function getStartDate(days) {
  if (!days) return null
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString()
}

/**
 * Main analytics dashboard page.
 *
 * Displays four KPI cards, a filter panel, four charts (acceptance-rate
 * timeline, error distribution bar chart, duration vs interactions scatter
 * plot, and code-quality timeline), and an insights panel.  All data is
 * loaded via the `useSessions` and `useMetrics` hooks and re-fetched when the
 * language or time-period filter changes.
 *
 * @returns {JSX.Element}
 */
function Dashboard() {
  const [filters, setFilters] = useState({
    language: null,
    timePeriod: 'all_time',
  })

  const sessionsFilters = useMemo(() => {
    const range = TIME_RANGES.find((r) => r.value === filters.timePeriod)
    return {
      language: filters.language,
      startDate: getStartDate(range?.days ?? null),
    }
  }, [filters.language, filters.timePeriod])

  const { sessions, loading: sessionsLoading, error: sessionsError } = useSessions(sessionsFilters)
  const { metrics, loading: metricsLoading, error: metricsError } = useMetrics(filters)

  const handleLanguageChange = (language) => {
    setFilters((prev) => ({ ...prev, language }))
  }

  const handleTimePeriodChange = (timePeriod) => {
    setFilters((prev) => ({ ...prev, timePeriod }))
  }

  const kpis = useMemo(() => {
    if (!sessions || sessions.length === 0) {
      return {
        totalSessions: 0,
        totalInteractions: 0,
        avgAcceptanceRate: '0.0',
        topLanguage: 'N/A',
      }
    }

    const langCounts = sessions.reduce((acc, s) => {
      acc[s.language] = (acc[s.language] || 0) + 1
      return acc
    }, {})
    const topLang = Object.entries(langCounts).sort((a, b) => b[1] - a[1])

    const ratesWithValues = sessions.filter((s) => s.acceptance_rate != null)
    const avgRate =
      ratesWithValues.length > 0
        ? ratesWithValues.reduce((sum, s) => sum + s.acceptance_rate, 0) / ratesWithValues.length
        : 0

    return {
      totalSessions: sessions.length,
      totalInteractions: sessions.reduce((sum, s) => sum + (s.interaction_count || 0), 0),
      avgAcceptanceRate: (avgRate * 100).toFixed(1),
      topLanguage: topLang.length > 0 ? topLang[0][0] : 'N/A',
    }
  }, [sessions])

  const loading = sessionsLoading || metricsLoading
  const fetchError = sessionsError || metricsError

  return (
    <div className="dashboard">
      {/* KPI Cards */}
      <div className="kpi-cards">
        <div className="kpi-card">
          <div className="kpi-icon">
            <BarChart3 size={24} />
          </div>
          <div className="kpi-info">
            <span className="kpi-label">Total Sessions</span>
            <span className="kpi-value">{loading ? '-' : kpis.totalSessions}</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon">
            <MessageSquare size={24} />
          </div>
          <div className="kpi-info">
            <span className="kpi-label">Total Interactions</span>
            <span className="kpi-value">{loading ? '-' : kpis.totalInteractions}</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon">
            <ThumbsUp size={24} />
          </div>
          <div className="kpi-info">
            <span className="kpi-label">Avg Acceptance Rate</span>
            <span className="kpi-value">{loading ? '-' : `${kpis.avgAcceptanceRate}%`}</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon">
            <Code size={24} />
          </div>
          <div className="kpi-info">
            <span className="kpi-label">Top Language</span>
            <span className="kpi-value">{loading ? '-' : kpis.topLanguage}</span>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="filters-panel">
        <h3>Filters</h3>
        <div className="filters-row">
          <LanguageFilter onLanguageChange={handleLanguageChange} />
          <div className="time-range-filter">
            <label>Time Range</label>
            <div className="time-range-buttons">
              {TIME_RANGES.map((range) => (
                <button
                  key={range.value}
                  className={`time-range-btn${filters.timePeriod === range.value ? ' active' : ''}`}
                  onClick={() => handleTimePeriodChange(range.value)}
                >
                  {range.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {fetchError && (
        <div className="error-state" role="alert">
          Error loading data: {fetchError}
        </div>
      )}

      {loading ? (
        <div className="loading-state">Loading dashboard data...</div>
      ) : (
        <>
          {/* Charts */}
          <div className="charts-grid">
            <div className="chart-card">
              <h3>Acceptance Rate Over Time</h3>
              <div className="chart-body">
                <Timeline
                  data={metrics?.acceptanceTrend || []}
                  title=""
                  yLabel="Acceptance Rate"
                />
              </div>
            </div>

            <div className="chart-card">
              <h3>Error Distribution</h3>
              <div className="chart-body">
                <ErrorDistribution data={metrics?.errorDistribution || {}} title="" />
              </div>
            </div>

            <div className="chart-card chart-card-wide">
              <h3>Duration vs Interactions</h3>
              <div className="chart-body">
                <ScatterPlot
                  data={sessions}
                  xKey="duration_seconds"
                  yKey="interaction_count"
                  sizeKey="error_count"
                  title=""
                />
              </div>
            </div>

            <div className="chart-card chart-card-wide">
              <h3>Code Quality Over Time</h3>
              <div className="chart-body">
                <Timeline
                  data={(metrics?.qualityMetrics || []).map((m) => ({
                    timestamp: m.timestamp,
                    value: m.code_quality_score,
                  }))}
                  title=""
                  yLabel="Quality Score"
                />
              </div>
            </div>
          </div>

          {/* Insights */}
          <InsightsPanel metrics={metrics} sessions={sessions} />
        </>
      )}
    </div>
  )
}

export default Dashboard
