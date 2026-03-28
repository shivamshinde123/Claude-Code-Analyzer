import React, { useState, useEffect } from 'react'
import { apiClient } from '../../api/client'

function LanguageFilter({ onLanguageChange }) {
  const [languages, setLanguages] = useState([])
  const [selected, setSelected] = useState('')

  useEffect(() => {
    const controller = new AbortController()

    apiClient
      .get('/api/sessions/stats/summary', { signal: controller.signal })
      .then((response) => {
        const langs = Object.keys(response.data.languages || {})
        setLanguages(langs)
      })
      .catch((err) => {
        if (err.name === 'CanceledError' || err.name === 'AbortError') return
        console.error('Error fetching languages:', err)
      })

    return () => {
      controller.abort()
    }
  }, [])

  const handleChange = (e) => {
    const value = e.target.value || null
    setSelected(e.target.value)
    onLanguageChange(value)
  }

  return (
    <div className="language-filter">
      <label>Language</label>
      <select value={selected} onChange={handleChange}>
        <option value="">All Languages</option>
        {languages.map((lang) => (
          <option key={lang} value={lang}>
            {lang}
          </option>
        ))}
      </select>
    </div>
  )
}

export default LanguageFilter
