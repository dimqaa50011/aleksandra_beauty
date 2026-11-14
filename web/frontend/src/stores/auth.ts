import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient, { setAccessToken } from '@/api/client'
import { getPlatform, initPlatform } from '@/utils/platform'
import bridge from '@vkontakte/vk-bridge'

export interface UserProfile {
  id: number
  name: string
  phone: string | null // Телефон может быть null, если вход через соцсеть
  email: string
  bonus_balance: number
  total_bookings: number
  total_spent: string
  consent_marketing: boolean
  years_with_us: number
  avatar: string | null
  favorite_service: { id: number; name: string; count: number } | null
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const user = ref<UserProfile | null>(null)
  const initialized = ref(false)
  
  // Флаг, если нужен телефон (для новых юзеров из соцсетей)
  const needsPhone = ref(false) 

  function setToken(newToken: string | null) {
    token.value = newToken
    setAccessToken(newToken)
  }

  // --- ОБЫЧНЫЙ ВХОД (PWA) ---
  async function login(phone: string, password: string) {
    const { data } = await apiClient.post('/auth/login/', { phone, password })
    setToken(data.access)
    await fetchMe()
    return data
  }

  // --- ВХОД ЧЕРЕЗ СОЦСЕТИ ---
  async function loginViaSocial() {
    const platform = await initPlatform()
    if (platform === 'pwa') return false // Если мы в обычном браузере, ничего не делаем

    try {
      let endpoint = ''
      let payload = {}

      if (platform === 'telegram') {
        endpoint = '/auth/telegram/'
        payload = { init_data: window.Telegram.WebApp.initData }
      } 
      else if (platform === 'max') {
        endpoint = '/auth/max/'
        payload = { init_data: window.WebApp.initData }
      } 
      else if (platform === 'vk') {
        endpoint = '/auth/vk/'
        // Для VK получаем параметры запуска
        const vkData = await bridge.send('VKWebAppGetLaunchParams')
        payload = { launch_params: vkData }
      }

      const { data } = await apiClient.post(endpoint, payload)
      setToken(data.access)
      await fetchMe()
      
      // Если бэкенд сказал, что это новый юзер без телефона
      if (data.is_new || !user.value?.phone) {
        needsPhone.value = true
      }

      return true
    } catch (e) {
      console.error('Ошибка соц. авторизации', e)
      return false
    }
  }

  // --- РЕГИСТРАЦИЯ (PWA) ---
  async function register(payload: {
    phone: string
    password: string
    password_confirm: string
    name?: string
    email?: string
    consent_pd: boolean
    consent_marketing?: boolean
    ref?: string
  }) {
    const { data } = await apiClient.post('/auth/register/', payload)
    setToken(data.access)
    await fetchMe()
    return data
  }

  async function fetchMe() {
    const { data } = await apiClient.get('/me/')
    user.value = data
    return data
  }

  async function updateProfile(payload: { name?: string; email?: string }) {
    const { data } = await apiClient.patch('/me/', payload)
    user.value = data
    return data
  }

  async function updateConsents(payload: { consent_marketing: boolean }) {
    const { data } = await apiClient.patch('/me/consents/', payload)
    if (user.value) {
      user.value.consent_marketing = data.consent_marketing
    }
  }

  async function logout() {
    try {
      await apiClient.post('/auth/logout/')
    } finally {
      setToken(null)
      user.value = null
      needsPhone.value = false
    }
  }

  async function tryRestoreSession() {
    try {
      const { data } = await apiClient.post('/auth/refresh/')
      setToken(data.access)
      await fetchMe()
    } catch {
      setToken(null)
      user.value = null
    } finally {
      initialized.value = true
    }
  }

  return {
    token, 
    user, 
    initialized,
    needsPhone, // <--- Экспортируем флаг
    login, 
    register, 
    fetchMe, 
    updateProfile, 
    updateConsents, 
    logout, 
    tryRestoreSession,
    loginViaSocial, // <--- Экспортируем новый метод
    setToken,
  }
})