<template>
  <div class="notif-detail-page">
    <div class="page-header">
      <van-icon name="arrow-left" size="24" @click="$router.push('/notifications')" />
      <h1>Уведомление</h1>
      <div style="width: 24px"></div>
    </div>

    <div v-if="loading" class="loading-center">
      <van-loading color="#f2a6b0" />
    </div>

    <div v-else-if="notif" class="content-container">
      <div class="notif-card">
        <h2>{{ notif.title }}</h2>
        <p class="date">{{ notif.created_at }}</p>
        <div class="body">{{ notif.body }}</div>
        
        <!-- Используем action_url и умный текст кнопки -->
        <div class="action-btn" v-if="notif.action_url">
          <van-button round block color="#f2a6b0" @click="goToUrl(notif.action_url)">
            {{ getButtonText(notif.action_url) }}
          </van-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import apiClient from '@/api/client'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const notif = ref<any>(null)

async function fetchDetail() {
  try {
    const { data } = await apiClient.get(`/notifications/${route.params.id}/`)
    notif.value = data
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

function goToUrl(url: string) {
  if (!url) return
  
  // Если ссылка внутренняя (начинается с /), используем vue-router
  if (url.startsWith('/')) {
    // Заменяем /cabinet/ на пустоту, так как роутер и так в base
    const cleanUrl = url.replace('/cabinet', '')
    router.push(cleanUrl)
  } else {
    // Если внешняя — открываем в новой вкладке
    window.open(url, '_blank')
  }
}

// Функция для красивого текста кнопки
function getButtonText(url: string) {
  if (!url) return 'Перейти'
  if (url.includes('/reviews/')) return '⭐ Оставить отзыв'
  if (url.includes('/appointments')) return 'Посмотреть запись'
  return 'Перейти'
}

onMounted(() => {
  fetchDetail()
})
</script>

<style scoped>
.notif-detail-page {
  min-height: 100vh;
  background-color: var(--bg-light, #fef9f7);
  padding: 24px 20px 60px;
  font-family: 'Inter', sans-serif;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 20px;
  font-weight: 700;
  margin: 0;
}

.notif-card {
  background: #fff;
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
}

h2 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-dark, #2d2a28);
  margin: 0 0 8px 0;
}

.date {
  font-size: 12px;
  color: var(--text-gray, #6b5f5a);
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0e8e5;
}

.body {
  font-size: 15px;
  line-height: 1.6;
  color: var(--text-dark, #2d2a28);
  margin-bottom: 24px;
  white-space: pre-line; /* Чтобы сохранялись переносы строк из текста */
}

.loading-center {
  display: flex;
  justify-content: center;
  padding: 40px;
}
</style>