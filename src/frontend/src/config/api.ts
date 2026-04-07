/**
 * API configuration
 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:6060'

/**
 * Create a full API URL from a relative path
 */
export function createApiUrl(path: string): string {
  // Remove leading slash if present to avoid double slashes
  const cleanPath = path.startsWith('/') ? path.slice(1) : path
  return `${API_BASE_URL}/${cleanPath}`
}