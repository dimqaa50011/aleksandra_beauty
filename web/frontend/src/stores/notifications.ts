import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '@/api/client'

export const useNotificationStore = defineStore('notifications', () => {
  const unreadCount = ref(0)

  async function fetchUnreadCount() {
    try {
      const { data } = await apiClient.get('/notifications/unread/')
      unreadCount.value = data.count
    } catch (e) {
      console.error(e)
    }
  }

  return { unreadCount, fetchUnreadCount }
})