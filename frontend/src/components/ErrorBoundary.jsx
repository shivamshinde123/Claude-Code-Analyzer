import React from 'react'

/**
 * Top-level error boundary that catches unhandled render errors.
 *
 * When any descendant component throws during rendering, this boundary
 * replaces the broken subtree with a simple error card and logs the full
 * error + component stack to the console.  A "Reload Page" button lets the
 * user recover without a manual browser refresh.
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error('Unhandled render error:', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-state" role="alert">
          <h3>Something went wrong</h3>
          <p>{this.state.error?.message || 'An unexpected error occurred.'}</p>
          <button
            className="btn"
            onClick={() => window.location.reload()}
          >
            Reload Page
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

export default ErrorBoundary
