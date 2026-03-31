import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { apiClient } from '../api/client'
import Timeline from '../components/Charts/Timeline'

/**
 * Session detail page.
 *
 * Fetches full session data (metadata, interactions, errors) and the
 * per-interaction timeline in parallel, then renders a metadata grid, an
 * optional quality-score chart, a scrollable interaction list, and an error
 * panel.
 *
 * The `sessionId` param is read from the URL via `useParams`.
 *
 * @returns {JSX.Element}
 */
function SessionDetail() {
  const { sessionId } = useParams()
  const [data, setData] = useState(null)
  const [timeline, setTimeline] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    Promise.all([
      apiClient.get(`/api/sessions/${sessionId}`),
      apiClient
        .get(`/api/timeline/session/${sessionId}`)
        .catch(() => ({ data: { timeline: [] } })),
    ])
      .then(([detailRes, timelineRes]) => {
        if (cancelled) return
        setData(detailRes.data)
        setTimeline(timelineRes.data.timeline || [])
      })
      .catch((err) => {
        if (cancelled) return
        console.error('Error fetching session detail:', err)
        setError(err.response?.status === 404 ? 'Session not found' : err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [sessionId])

  if (loading) {
    return <div className="loading-state">Loading session details...</div>
  }

  if (error) {
    return (
      <div className="error-state">
        <p>{error}</p>
        <Link to="/sessions" className="btn">
          Back to Sessions
        </Link>
      </div>
    )
  }

  const session = data?.session || data
  const summary = data?.summary || {}
  const interactions = session?.interactions || []
  const errors = session?.errors || []

  if (!session) {
    return (
      <div className="error-state">
        <p>Session data could not be loaded.</p>
        <Link to="/sessions" className="btn">
          Back to Sessions
        </Link>
      </div>
    )
  }

  const qualityData = timeline.map((t) => ({
    timestamp: t.timestamp,
    value: t.quality_score ?? 0,
  }))

  return (
    <div className="session-detail">
      <Link to="/sessions" className="back-link">
        <ArrowLeft size={16} /> Back to Sessions
      </Link>

      <h2>Session Detail</h2>

      {/* Session metadata */}
      <div className="detail-meta">
        <div className="meta-item">
          <span className="meta-label">Language</span>
          <span className="badge">{session.language}</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Status</span>
          <span className={`status status-${session.status}`}>{session.status}</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Start</span>
          <span>{new Date(session.start_time).toLocaleString()}</span>
        </div>
        {session.end_time && (
          <div className="meta-item">
            <span className="meta-label">End</span>
            <span>{new Date(session.end_time).toLocaleString()}</span>
          </div>
        )}
        <div className="meta-item">
          <span className="meta-label">Duration</span>
          <span>
            {session.duration_seconds != null
              ? `${(session.duration_seconds / 60).toFixed(1)} min`
              : '-'}
          </span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Acceptance Rate</span>
          <span>
            {session.acceptance_rate != null
              ? `${(session.acceptance_rate * 100).toFixed(1)}%`
              : '-'}
          </span>
        </div>
        {session.project_name && (
          <div className="meta-item">
            <span className="meta-label">Project</span>
            <span>{session.project_name}</span>
          </div>
        )}
      </div>

      {/* Quality timeline */}
      {qualityData.length > 0 && (
        <div className="chart-card">
          <h3>Quality Score Over Session</h3>
          <div className="chart-body">
            <Timeline data={qualityData} title="" yLabel="Quality Score" />
          </div>
        </div>
      )}

      {/* Interactions list */}
      <div className="interactions-section">
        <h3>Interactions ({interactions.length})</h3>
        {interactions.length === 0 ? (
          <p className="no-data">No interactions recorded.</p>
        ) : (
          <div className="interactions-list">
            {interactions.map((interaction, idx) => (
              <div key={interaction.id || idx} className="interaction-card">
                <div className="interaction-header">
                  <span className="interaction-seq">#{interaction.sequence_number || idx + 1}</span>
                  <span className={`badge badge-${interaction.interaction_type}`}>
                    {interaction.interaction_type}
                  </span>
                  <span className={interaction.was_accepted ? 'tag-accepted' : 'tag-rejected'}>
                    {interaction.was_accepted ? 'Accepted' : 'Rejected'}
                  </span>
                  {interaction.was_modified && <span className="tag-modified">Modified</span>}
                </div>
                <div className="interaction-body">
                  <div className="prompt-section">
                    <strong>Prompt:</strong>
                    <pre>{interaction.human_prompt}</pre>
                  </div>
                  <div className="response-section">
                    <strong>Response:</strong>
                    <pre>{interaction.claude_response}</pre>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Errors */}
      {errors.length > 0 && (
        <div className="errors-section">
          <h3>Errors ({errors.length})</h3>
          <div className="errors-list">
            {errors.map((err, idx) => (
              <div key={err.id || idx} className={`error-card severity-${err.severity}`}>
                <div className="error-header">
                  <span className="badge">{err.error_type}</span>
                  <span className={`severity severity-${err.severity}`}>{err.severity}</span>
                </div>
                <pre className="error-message">{err.error_message}</pre>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default SessionDetail
