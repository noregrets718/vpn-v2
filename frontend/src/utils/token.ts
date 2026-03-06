 const ACCESS_KEY = 'access_token'
  const REFRESH_KEY = 'refresh_token'

  export function getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_KEY)
  }

  export function getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_KEY)
  }

  export function setTokens(access: string, refresh: string): void {
    localStorage.setItem(ACCESS_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  }

  export function clearTokens(): void {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  }

  export function parseJwtPayload(token: string): Record<string, unknown> {
    const base64 = token.split('.')[1]!
    const json = atob(base64.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(json)
  }

  export function tokenExpiresIn(token: string): number {
    const payload = parseJwtPayload(token)
    const exp = payload.exp as number
    return exp - Math.floor(Date.now() / 1000)
  }

  export function isTokenExpiringSoon(token: string, thresholdSeconds = 120): boolean {
    return tokenExpiresIn(token) <= thresholdSeconds
  }