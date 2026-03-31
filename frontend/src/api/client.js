import axios from 'axios'

/**
 * Base URL for API requests.
 * Falls back to the local backend dev server when VITE_API_URL is not set.
 */
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Pre-configured Axios instance shared across all API modules.
 *
 * Sets the base URL, a 10-second timeout, and JSON content-type.  A
 * response interceptor logs API errors to the console before re-throwing
 * them so callers can handle them via `.catch()`.
 */
export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export default apiClient
