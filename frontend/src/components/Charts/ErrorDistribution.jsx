import Plot from "react-plotly.js"

function themeColor(name, fallback) {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

function generatePalette(n, baseHex) {
  // Create n tints from the base accent
  const base = baseHex.replace('#','')
  const full = base.length === 3 ? base.split('').map((c)=>c+c).join('') : base
  const r = parseInt(full.slice(0,2),16), g=parseInt(full.slice(2,4),16), b=parseInt(full.slice(4,6),16)
  const colors=[]
  for (let i=0;i<n;i++){
    const f = 0.25 + (0.7 * i/(Math.max(n-1,1))) // from 25% to 95%
    const rr = Math.round(r + (255-r)*f)
    const gg = Math.round(g + (255-g)*f)
    const bb = Math.round(b + (255-b)*f)
    colors.push(`rgb(${rr}, ${gg}, ${bb})`)
  }
  return colors
}

function ErrorDistribution({ data, title }) {
  if (!data || Object.keys(data).length === 0) {
    return <div className="chart-placeholder">No error data available</div>
  }

  const errorTypes = Object.keys(data)
  const counts = Object.values(data)
  const ACCENT = themeColor('--accent', '#C084FC')
  const colors = generatePalette(counts.length, ACCENT)

  return (
    <Plot
      data={[
        {
          x: errorTypes,
          y: counts,
          type: 'bar',
          marker: {
            color: colors,
            line: { width: 0 },
          },
          hovertemplate: '<b>%{x}</b><br>Count: %{y}<extra></extra>',
        },
      ]}
      layout={{
        title: { text: title, font: { size: 14 } },
        xaxis: { title: 'Error Type', gridcolor: '#1f2636', color: '#A5A7BE' },
        yaxis: { title: 'Count', gridcolor: '#1f2636', color: '#A5A7BE' },
        margin: { b: 60, l: 60, r: 30, t: 40 },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        bargap: 0.3,
        font: { color: '#E6E7F0' },
      }}
      useResizeHandler
      style={{ width: '100%', height: '100%' }}
      config={{ displayModeBar: false, responsive: true }}
    />
  )
}

export default ErrorDistribution