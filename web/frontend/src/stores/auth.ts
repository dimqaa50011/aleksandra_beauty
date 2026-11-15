import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient, { setAccessToken } from '@/api/client'
import { initPlatform } from '@/utils/platform'
import bridge from '@vkontakte/vk-bridge'

export interface UserProfile {
  id: number
  name: string
  phone: string | null
  email: string
  bonus_balance: number
  bonus_expiring_soon: number // <--- НОВОЕ ПОЛЕ (общая сумма сгорающих)
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
  const needsPhone = ref(false) 

  function setToken(newToken: string | null) {
    token.value = newToken
    setAccessToken(newToken)
  }

  async function login(phone: string, password: string) {
    const { data } = await apiClient.post('/auth/login/', { phone, password })
    setToken(data.access)
    await fetchMe()
    return data
  }

  async function loginViaSocial() {
    const platform = await initPlatform()
    if (platform === 'pwa') return false

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
        const urlParams = new URLSearchParams(window.location.search)
        const vkParams: Record<string, string> = {}
        urlParams.forEach((value, key) => {
          if (key.startsWith('vk_')) vkParams[key] = value
        })
        
        if (Object.keys(vkParams).length > 0) {
          payload = { launch_params: vkParams }
        } else {
          const vkData = await bridge.send('VKWebAppGetLaunchParams')
          payload = { launch_params: vkData }
        }
      }

      const { data } = await apiClient.post(endpoint, payload)
      setToken(data.access)
      await fetchMe()
      
      if (data.is_new || !user.value?.phone) {
        needsPhone.value = true
      }
      return true
    } catch (e) {
      console.error('Ошибка соц. авторизации', e)
      return false
    }
  }

  async function register(payload: any) {
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
    token, user, initialized, needsPhone,
    login, register, fetchMe, updateProfile, updateConsents, logout, tryRestoreSession, loginViaSocial, setToken,
  }
})