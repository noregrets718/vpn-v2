 import { getAccessToken, getRefreshToken, setTokens, clearTokens, isTokenExpiringSoon } from '@/utils/token'

  const BASE_URL = '/api'

  let refreshPromise: Promise<void> | null = null

  export async function refreshTokens(): Promise<void> {
    const rt = getRefreshToken()
    if (!rt) throw new Error('No refresh token')

    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: rt }),
    })

    if (!res.ok) {
      clearTokens()
      window.location.href = '/login'
      throw new Error('Refresh failed')
    }

    const data = await res.json()
    setTokens(data.access_token, data.refresh_token)
  }

  async function ensureFreshToken(): Promise<void> {
    const token = getAccessToken()
    if (!token || !isTokenExpiringSoon(token)) return

    if (!refreshPromise) {
      refreshPromise = refreshTokens().finally(() => { refreshPromise = null })
    }
    await refreshPromise
  }

  async function request(endpoint: string, { method = 'GET', body, headers = {} }: { method?: string; body?: unknown; headers?: Record<string, string> } = {}) {
    // Проактивный refresh перед запросом
    await ensureFreshToken()

    const token = getAccessToken()

    const config: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...headers,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    }

    if (body !== undefined) {
      config.body = JSON.stringify(body)
    }

    let response = await fetch(`${BASE_URL}${endpoint}`, config)

    // Реактивный refresh при 401
    if (response.status === 401) {
      try {
        if (!refreshPromise) {
          refreshPromise = refreshTokens().finally(() => { refreshPromise = null })
        }
        await refreshPromise

        const newToken = getAccessToken()
        config.headers = {
          ...config.headers as Record<string, string>,
          Authorization: `Bearer ${newToken}`,
        }
        response = await fetch(`${BASE_URL}${endpoint}`, config)
      } catch {
        throw new Error('Unauthorized')
      }
    }

    if (!response.ok) {
      let message: string
      try {
        const err = await response.json()
        message = err.detail || err.message || response.statusText
      } catch {
        message = response.statusText
      }
      throw new Error(message)
    }

    if (response.status === 204) return null

    return response.json()
  }

  export const api = {
    get:   (url: string, headers?: Record<string, string>) => request(url, { headers }),
    post:  (url: string, body?: unknown, headers?: Record<string, string>) => request(url, { method: 'POST', body, headers }),
    put:   (url: string, body?: unknown, headers?: Record<string, string>) => request(url, { method: 'PUT', body, headers }),
    patch: (url: string, body?: unknown, headers?: Record<string, string>) => request(url, { method: 'PATCH', body, headers }),
    del:   (url: string, headers?: Record<string, string>) => request(url, { method: 'DELETE', headers }),
  }

  export default api