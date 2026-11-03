<template>
  <div class="notifications-page">
    <div class="page-header">
      <h1>Уведомления</h1>
    </div>

    <div v-if="loading" class="loading-center">
      <van-loading color="#f2a6b0" />
    </div>
    
    <div v-else-if="!notifications.length" class="empty-state">
      <van-icon name="bell-o" size="48" color="#d1d5db" />
      <p>У вас пока нет уведомлений</p>
    </div>

    <div v-else class="list-container">
      <div 
        v-for="notif in notifications" 
        :key="notif.id" 
        class="notif-item"
        :class="{ 'unread': !notif.is_read }"
        @click="goToDetail(notif)"
      >
        <div class="notif-icon" v-if="!notif.is_read"></div>
        <div class="notif-content">
          <div class="notif-header">
            <span class="notif-title">{{ notif.title }}</span>
            <span class="notif-date">{{ notif.created_at }}</span>
          </div>
          <div class="notif-body">{{ notif.body }}</div>
        </div>
      </div>
    </div>

    <BottomTabbar />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import apiClient from '@/api/client'
import BottomTabbar from '@/components/BottomTabbar.vue'
import { useNotificationStore } from '@/stores/notifications'

const router = useRouter()
const notifStore = useNotificationStore()
const loading = ref(true)
const notifications = ref<any[]>([])

async function fetchNotifications() {
  try {
    const { data } = await apiClient.get('/notifications/')
    notifications.value = data.notifications
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

function goToDetail(notif: any) {
  router.push(`/notifications/${notif.id}`)
}

onMounted(() => {
  fetchNotifications()
  // Обновляем счетчик, так как мы могли отметить их прочитанными
  setTimeout(() => notifStore.fetchUnreadCount(), 500)
})
</script>

<style scoped>
.notifications-page {
  min-height: 100vh;
  padding-bottom: 80px;
  background-color: var(--bg-light, #fef9f7);
  font-family: 'Inter', sans-serif;
}

.page-header {
  padding: 24px 16px 16px;
  text-align: center;
}

.page-header h1 {
  font-size: 20px;
  font-weight: 700;
  margin: 0;
}

.list-container {
  padding: 0 16px;
}

.notif-item {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  display: flex;
  gap: 12px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.02);
  border: 1px solid transparent;
  cursor: pointer;
}

.notif-item.unread {
  border-color: #f9d1d6;
  background: #fffafb;
}

.notif-icon {
  width: 8px;
  height: 8px;
  background: #f2a6b0;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}

.notif-content {
  flex: 1;
}

.notif-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 4px;
}

.notif-title {
  font-weight: 600;
  font-size: 15px;
  color: var(--text-dark, #2d2a28);
}

.notif-date {
  font-size: 11px;
  color: var(--text-gray, #6b5f5a);
}

.notif-body {
  font-size: 13px;
  color: var(--text-gray, #6b5f5a);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.loading-center {
  display: flex;
  justify-content: center;
  padding: 40px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-gray, #6b5f5a);
}
</style>