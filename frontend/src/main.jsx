/**
 * Application entry point.
 *
 * Mounts the React application inside a StrictMode wrapper so that
 * potential side-effect problems are surfaced during development.
 * Note: in development, StrictMode causes effects to run twice.
 */
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles/globals.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
