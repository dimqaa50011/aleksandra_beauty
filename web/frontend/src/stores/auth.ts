import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient, { setAccessToken } from '@/api/client'

export interface UserProfile {
  id: number
  name: string
  phone: string
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
    }
  }

  async function tryRestoreSession() {
    // Пробуем восстановить сессию через refresh-cookie при первом заходе
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
    token, user, initialized,
    login, register, fetchMe, updateProfile, updateConsents, logout, tryRestoreSession,
    setToken,
  }
})