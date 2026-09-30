const BASE_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'

/** Shape returned by GET /health. */
export interface HealthResponse {
  status: string
  database: string
  tables: number
}

/** Small typed wrapper around fetch. Throws if the response is not 2xx. */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    throw new Error(`API error ${response.status} on ${path}`)
  }
  return (await response.json()) as T
}

export const getHealth = () => apiFetch<HealthResponse>('/health')
