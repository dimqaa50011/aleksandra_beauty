import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { requiresGuest: true } },
    { path: '/register', name: 'register', component: () => import('@/views/RegisterView.vue'), meta: { requiresGuest: true } },
    { path: '/', name: 'home', component: () => import('@/views/HomeView.vue'), meta: { requiresAuth: true } },
    { path: '/booking', name: 'booking', component: () => import('@/views/BookingView.vue'), meta: { requiresAuth: true } },
    { path: '/appointments', name: 'appointments', component: () => import('@/views/AppointmentsView.vue'), meta: { requiresAuth: true } },
    { path: '/bonuses', name: 'bonuses', component: () => import('@/views/BonusesView.vue'), meta: { requiresAuth: true } },
    { path: '/profile', name: 'profile', component: () => import('@/views/ProfileView.vue'), meta: { requiresAuth: true } },
    { path: '/notifications', name: 'notifications', component: () => import('@/views/NotificationsView.vue'), meta: { requiresAuth: true } },
    { path: '/notifications/:id', name: 'notification-detail', component: () => import('@/views/NotificationDetailView.vue'), meta: { requiresAuth: true } },
    { path: '/certificates/:id', name: 'certificate-detail', component: () => import('@/views/CertificateDetailView.vue'), meta: { requiresAuth: true } },
    { path: '/reviews/:token', name: 'review-form', component: () => import('@/views/ReviewFormView.vue'), meta: { requiresAuth: true } },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  if (!authStore.initialized) {
    try {
      // 1. Пробуем по кукам
      await authStore.tryRestoreSession()
      
      // 2. Если не вышло, пробуем соцсети (с таймаутом, чтобы не зависнуть)
      if (!authStore.token) {
        await Promise.race([
          authStore.loginViaSocial(),
          new Promise((_, reject) => setTimeout(() => reject(new Error('Social auth timeout')), 3000))
        ])
      }
    } catch (e) {
      console.warn('Auth init failed or timeout:', e)
      // Ошибку не пробрасываем, чтобы роутер не завис
    } finally {
      // В любом случае ставим флаг, что инициализация завершена
      authStore.initialized = true
    }
  }

  if (to.meta.requiresAuth && !authStore.token) {
    return { name: 'login' }
  }
  
  if (to.meta.requiresGuest && authStore.token) {
    return { name: 'home' }
  }
})

export default router
