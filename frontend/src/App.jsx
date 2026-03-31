import React from 'react'
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom'
import { BarChart3 } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import Sessions from './pages/Sessions'
import SessionDetail from './pages/SessionDetail'
import ErrorBoundary from './components/ErrorBoundary'

/**
 * Root application component.
 *
 * Sets up client-side routing with a top navigation bar that links to the
 * Dashboard and Sessions pages.  All routes are wrapped in an ErrorBoundary
 * so uncaught render errors display a friendly fallback instead of a blank
 * screen.
 *
 * @returns {JSX.Element} The full application shell.
 */
function App() {
  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="container nav-container">
            <NavLink to="/" className="logo">
              <BarChart3 size={24} />
              <span>AgentPulse</span>
            </NavLink>
            <ul className="nav-links">
              <li>
                <NavLink to="/" end>
                  Dashboard
                </NavLink>
              </li>
              <li>
                <NavLink to="/sessions">Sessions</NavLink>
              </li>
            </ul>
          </div>
        </nav>

        <main className="main-content container">
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/sessions" element={<Sessions />} />
              <Route path="/sessions/:sessionId" element={<SessionDetail />} />
            </Routes>
          </ErrorBoundary>
        </main>
      </div>
    </Router>
  )
}

export default App