import Plot from "react-plotly.js"

/**
 * Read a CSS custom property value from the document root.
 *
 * @param {string} name    - CSS variable name, e.g. `'--accent'`.
 * @param {string} fallback - Value returned when the variable is undefined or
 *                            the code runs outside a browser (e.g. SSR).
 * @returns {string}
 */
function themeColor(name, fallback) {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

/**
 * Convert a hex colour string to an rgba() string with the given opacity.
 * Supports 3-character shorthand hex values.
 *
 * @param {string} hex   - Hex colour (e.g. `'#C084FC'` or `'#C8F'`).
 * @param {number} alpha - Opacity between 0 and 1 (default 0.15).
 * @returns {string} CSS rgba() colour string.
 */
function hexToRgba(hex, alpha = 0.15) {
  try {
    const m = hex.replace('#', '')
    const full = m.length === 3 ? m.split('').map((c) => c + c).join('') : m
    const bigint = parseInt(full, 16)
    const r = (bigint >> 16) & 255
    const g = (bigint >> 8) & 255
    const b = bigint & 255
    return `rgba(${r}, ${g}, ${b}, ${alpha})`
  } catch {
    return 'rgba(192, 132, 252, 0.15)'
  }
}

/**
 * Line chart that renders a time-series of values using Plotly.
 *
 * Each data point must have a `timestamp` (or `date`) key and a `value`
 * (or `acceptance_rate` / `rate`) key.  The chart fills the area below the
 * line using a translucent version of the accent colour pulled from the CSS
 * theme.
 *
 * @param {{ data: object[], title: string, yLabel: string }} props
 * @returns {JSX.Element}
 */
function Timeline({ data, title, yLabel }) {
  if (!data || data.length === 0) {
    return <div className="chart-placeholder">No timeline data available</div>
  }

  const ACCENT = themeColor('--accent', '#C084FC')
  const ACCENT_FILL = hexToRgba(ACCENT, 0.12)

  const timestamps = data.map((d) => d.timestamp || d.date)
  const values = data.map((d) => d.value ?? d.acceptance_rate ?? d.rate ?? 0)

  return (
    <Plot
      data={[
        {
          x: timestamps,
          y: values,
          type: 'scatter',
          mode: 'lines+markers',
          line: { color: ACCENT, width: 2 },
          marker: { size: 6, color: ACCENT },
          fill: 'tozeroy',
          fillcolor: ACCENT_FILL,
          hovertemplate: '<b>%{x}</b><br>%{y:.2f}<extra></extra>',
        },
      ]}
      layout={{
        title: { text: title, font: { size: 14 } },
        xaxis: { title: 'Time', gridcolor: '#1f2636', color: '#A5A7BE' },
        yaxis: { title: yLabel, gridcolor: '#1f2636', color: '#A5A7BE' },
        hovermode: 'x unified',
        margin: { b: 50, l: 60, r: 30, t: 40 },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { color: '#E6E7F0' },
      }}
      useResizeHandler
      style={{ width: '100%', height: '100%' }}
      config={{ displayModeBar: false, responsive: true }}
    />
  )
}

export default Timeline