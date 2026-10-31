import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresGuest: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { requiresGuest: true },
    },
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/booking',
      name: 'booking',
      component: () => import('@/views/BookingView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/appointments',
      name: 'appointments',
      component: () => import('@/views/AppointmentsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/bonuses',
      name: 'bonuses',
      component: () => import('@/views/BonusesView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/ProfileView.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  // Один раз при старте приложения пробуем восстановить сессию по refresh-cookie
  if (!authStore.initialized) {
    await authStore.tryRestoreSession()
  }

  if (to.meta.requiresAuth && !authStore.token) {
    return { name: 'login' }
  }
  if (to.meta.requiresGuest && authStore.token) {
    return { name: 'home' }
  }
})

export default router