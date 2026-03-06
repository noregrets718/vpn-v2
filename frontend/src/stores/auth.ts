import { defineStore } from 'pinia'
  import api from '@/api/client'
  import { refreshTokens } from '@/api/client'
  import router from '@/router'
  import { getAccessToken, setTokens, clearTokens, tokenExpiresIn } from '@/utils/token'

  let refreshTimer: ReturnType<typeof setTimeout> | null = null

  export const useAuthStore = defineStore('auth', {
    state: () => ({
      token: getAccessToken(),
      user: null as Record<string, unknown> | null,
      ready: false,
    }),

    getters: {
      isAuthenticated: (state) => !!state.token,
    },

    actions: {
      async login(email: string, password: string) {
        const response = await api.post('/auth/login', { email, password })
        setTokens(response.access_token, response.refresh_token)
        this.token = response.access_token
        await this.fetchUser()
        this.scheduleRefresh()
        return response
      },

      async register(email: string, password: string) {
        const response = await api.post('/auth/register', { email, password })
        setTokens(response.access_token, response.refresh_token)
        this.token = response.access_token
        await this.fetchUser()
        this.scheduleRefresh()
        return response
      },

      logout() {
        this.token = null
        this.user = null
        if (refreshTimer) {
          clearTimeout(refreshTimer)
          refreshTimer = null
        }
        clearTokens()
        router.push('/login')
      },

      async fetchUser() {
        const response = await api.get('/auth/me')
        this.user = response
      },

      scheduleRefresh() {
        if (refreshTimer) {
          clearTimeout(refreshTimer)
          refreshTimer = null
        }

        const token = getAccessToken()
        if (!token) return

        const expiresIn = tokenExpiresIn(token)
        const delay = Math.max((expiresIn - 120) * 1000, 0)

        refreshTimer = setTimeout(async () => {
          try {
            await refreshTokens()
            this.token = getAccessToken()
            this.scheduleRefresh()
          } catch {
            this.logout()
          }
        }, delay)
      },

      async init() {
        if (this.token) {
          try {
            await this.fetchUser()
            this.scheduleRefresh()
          } catch {
            this.logout()
          }
        }
        this.ready = true
      },
    },
  })