import { createRouter, createWebHistory } from 'vue-router'
  import DashboardView from '../views/DashboardView.vue'
  import { useAuthStore } from '@/stores/auth'

  const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
      {
        path: '/',
        name: 'Dashboard',
        component: DashboardView,
      },
      {
        path: '/login',
        name: 'Login',
        component: () => import('../views/LoginView.vue'),
      },
    ],
  })

  router.beforeEach(async (to) => {
    const authStore = useAuthStore()

    if (!authStore.ready) {
      await authStore.init()
    }

    if (!authStore.isAuthenticated && to.name !== 'Login') {
      return { name: 'Login' }
    }

    if (authStore.isAuthenticated && to.name === 'Login') {
      return { name: 'Dashboard' }
    }
  })

  export default router
