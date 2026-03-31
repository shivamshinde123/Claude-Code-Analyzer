import Plot from "react-plotly.js"

/**
 * Read a CSS custom property value from the document root.
 *
 * @param {string} name     - CSS variable name, e.g. `'--accent'`.
 * @param {string} fallback - Value returned when the variable is undefined.
 * @returns {string}
 */
function themeColor(name, fallback) {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

/**
 * Return a single tint of *baseHex* blended towards white by factor *f*.
 *
 * @param {string} baseHex - Source hex colour.
 * @param {number} f       - Tint factor between 0 (original) and 1 (white).
 * @returns {string} CSS `rgb()` colour string.
 */
function tint(baseHex, f=0.5){
  const base = baseHex.replace('#','')
  const full = base.length===3? base.split('').map((c)=>c+c).join(''): base
  const r = parseInt(full.slice(0,2),16), g=parseInt(full.slice(2,4),16), b=parseInt(full.slice(4,6),16)
  const rr = Math.round(r + (255-r)*f)
  const gg = Math.round(g + (255-g)*f)
  const bb = Math.round(b + (255-b)*f)
  return `rgb(${rr}, ${gg}, ${bb})`
}

/**
 * Scatter plot that visualises sessions as points on an X/Y plane.
 *
 * - X axis: duration in minutes (when `xKey === 'duration_seconds'`) or the
 *   raw numeric field.
 * - Y axis: the value of `yKey` (e.g. `interaction_count`).
 * - Marker size: scaled from the optional `sizeKey` field (e.g. `error_count`).
 * - Marker colour: one accent tint per unique language.
 *
 * @param {{
 *   data: object[],
 *   xKey: string,
 *   yKey: string,
 *   sizeKey?: string,
 *   title: string
 * }} props
 * @returns {JSX.Element}
 */
function ScatterPlot({ data, xKey, yKey, sizeKey, title }) {
  if (!data || data.length === 0) {
    return <div className="chart-placeholder">No scatter data available</div>
  }

  const ACCENT = themeColor('--accent', '#C084FC')

  // Convert duration to minutes for consistent display
  const toMinutes = xKey === 'duration_seconds'
  const xValues = data.map((d) => {
    const raw = d[xKey] ?? 0
    return toMinutes ? +(raw / 60).toFixed(1) : raw
  })
  const yValues = data.map((d) => d[yKey] ?? 0)
  const sizeValues = sizeKey
    ? data.map((d) => Math.max((d[sizeKey] ?? 0) * 5 + 8, 8))
    : data.map(() => 10)
  const hoverText = data.map(
    (d) =>
      `Language: ${d.language || 'N/A'}<br>` +
      `Duration: ${((d.duration_seconds || 0) / 60).toFixed(1)} min<br>` +
      `Interactions: ${d.interaction_count || 0}<br>` +
      `Errors: ${d.error_count || 0}`
  )

  // Color all points with accent tints by language (max 6 variants)
  const languages = [...new Set(data.map((d) => d.language))]
  const palette = [0.1,0.25,0.4,0.55,0.7,0.85].map((f)=>tint(ACCENT,f))
  const colorMap = {}
  languages.forEach((lang, i) => { colorMap[lang] = palette[i % palette.length] })
  const colors = data.map((d) => colorMap[d.language] || ACCENT)

  const xLabel = toMinutes ? 'Duration (minutes)' : xKey
  const yLabel = yKey === 'interaction_count' ? 'Interactions' : yKey

  return (
    <Plot
      data={[
        {
          x: xValues,
          y: yValues,
          type: 'scatter',
          mode: 'markers',
          marker: {
            size: sizeValues,
            color: colors,
            opacity: 0.8,
            line: { width: 1, color: '#0b0f16' },
          },
          text: hoverText,
          hoverinfo: 'text',
        },
      ]}
      layout={{
        title: { text: title, font: { size: 14 } },
        xaxis: { title: xLabel, gridcolor: '#1f2636', color: '#A5A7BE' },
        yaxis: { title: yLabel, gridcolor: '#1f2636', color: '#A5A7BE' },
        margin: { b: 60, l: 60, r: 30, t: 40 },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        hovermode: 'closest',
        font: { color: '#E6E7F0' },
      }}
      useResizeHandler
      style={{ width: '100%', height: '100%' }}
      config={{ displayModeBar: false, responsive: true }}
    />
  )
}

export default ScatterPlot