import React from 'react'
import { TrendingUp, TrendingDown, AlertTriangle, CheckCircle, Zap, Code } from 'lucide-react'

/**
 * Panel that derives and displays key insights from the current metrics.
 *
 * Generates up to five insight cards covering:
 * - The language with the highest acceptance rate
 * - The most frequently occurring error type
 * - The error recovery rate
 * - The overall code-quality trend (improving / stable / declining)
 * - The average number of interactions per session
 *
 * Renders a "no data" placeholder when there are not enough metrics yet.
 *
 * @param {{ metrics: object|null, sessions: object[] }} props
 * @returns {JSX.Element}
 */
function InsightsPanel({ metrics, sessions }) {
  const insights = []

  // Best language by acceptance rate
  if (metrics?.byLanguage && Object.keys(metrics.byLanguage).length > 0) {
    const entries = Object.entries(metrics.byLanguage).sort((a, b) => b[1] - a[1])
    const [bestLang, bestRate] = entries[0]
    insights.push({
      icon: <CheckCircle size={20} />,
      title: 'Best Language',
      description: `${bestLang} has ${(bestRate * 100).toFixed(1)}% acceptance rate`,
      type: 'success',
    })
  }

  // Most common error
  if (metrics?.errorDistribution && Object.keys(metrics.errorDistribution).length > 0) {
    const entries = Object.entries(metrics.errorDistribution).sort((a, b) => b[1] - a[1])
    const [errorType, count] = entries[0]
    insights.push({
      icon: <AlertTriangle size={20} />,
      title: 'Most Common Error',
      description: `${errorType} errors (${count} occurrences)`,
      type: 'warning',
    })
  }

  // Recovery rate
  if (metrics?.recoveryRate > 0) {
    insights.push({
      icon: <Zap size={20} />,
      title: 'Error Recovery',
      description: `${(metrics.recoveryRate * 100).toFixed(1)}% of errors recovered in next interaction`,
      type: metrics.recoveryRate > 0.7 ? 'success' : 'warning',
    })
  }

  // Quality trend
  if (metrics?.qualityTrend) {
    const isImproving = metrics.qualityTrend === 'improving'
    insights.push({
      icon: isImproving ? <TrendingUp size={20} /> : <TrendingDown size={20} />,
      title: 'Quality Trend',
      description: `Code quality is ${metrics.qualityTrend} (avg score: ${(metrics.avgQualityScore * 100).toFixed(0)}%)`,
      type: isImproving ? 'success' : metrics.qualityTrend === 'stable' ? 'info' : 'warning',
    })
  }

  // Session productivity
  if (sessions && sessions.length > 0) {
    const avgInteractions =
      sessions.reduce((sum, s) => sum + (s.interaction_count || 0), 0) / sessions.length
    insights.push({
      icon: <Code size={20} />,
      title: 'Avg Session Size',
      description: `${avgInteractions.toFixed(1)} interactions per session`,
      type: 'info',
    })
  }

  return (
    <div className="insights-panel">
      <h3>Key Insights</h3>
      {insights.length > 0 ? (
        <div className="insights-grid">
          {insights.map((insight) => (
            <div key={`${insight.type}-${insight.title}`} className={`insight-card insight-${insight.type}`}>
              <div className="insight-icon">{insight.icon}</div>
              <div className="insight-content">
                <h4>{insight.title}</h4>
                <p>{insight.description}</p>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="no-insights">No insights available yet. Collect more session data.</p>
      )}
    </div>
  )
}

export default InsightsPanel
