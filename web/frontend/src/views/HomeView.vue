<template>
  <div class="home-page">
    <!-- Хедер с приветствием -->
    <div class="header">
      <div class="greeting">
        <h1>Привет, {{ userName }}!</h1>
        <p>Рады видеть вас снова</p>
      </div>
      
      <!-- Динамическая аватарка -->
      <div class="avatar-wrapper">
        <img v-if="user?.avatar" :src="user.avatar" class="avatar-img" alt="Аватар" />
        <div v-else class="avatar">
          {{ userName.charAt(0).toUpperCase() }}
        </div>
      </div>
    </div>

    <!-- Блок ближайшей записи -->
    <div class="section">
      <h2 class="section-title">Ближайший визит</h2>
      
      <div v-if="loading" class="loading-block">
        <van-loading color="#f2a6b0" size="24px">Загружаем...</van-loading>
      </div>

      <div v-else-if="nextAppointment" class="appointment-card" @click="$router.push('/appointments')">
        <div class="appt-date">
          <span class="day">{{ formatDate(nextAppointment.appointment_datetime, 'DD') }}</span>
          <span class="month">{{ formatDate(nextAppointment.appointment_datetime, 'MMM') }}</span>
        </div>
        <div class="appt-info">
          <div class="appt-time">{{ formatDate(nextAppointment.appointment_datetime, 'HH:mm') }}</div>
          <div class="appt-services">{{ getServicesText(nextAppointment) }}</div>
        </div>
        <van-icon name="arrow" class="appt-arrow" />
      </div>

      <div v-else class="empty-card">
        <p>У вас пока нет активных записей</p>
        <van-button round type="primary" class="brand-btn" to="/booking">Записаться</van-button>
      </div>
    </div>

    <!-- Блок бонусов -->
    <div class="section">
      <h2 class="section-title">Ваши бонусы</h2>
      <div class="bonus-card" @click="$router.push('/bonuses')">
        <div class="bonus-info">
          <span class="bonus-value">{{ user?.bonus_balance || 0 }}</span>
          <span class="bonus-label">бонусов на счету</span>
        </div>
        <van-icon name="gift" size="32" color="#f2a6b0" />
      </div>
    </div>

    <!-- Быстрые действия -->
    <div class="section">
      <h2 class="section-title">Быстрые действия</h2>
      <div class="quick-actions">
        <div class="action-item" @click="$router.push('/booking')">
          <div class="icon-circle"><van-icon name="add-o" size="24" /></div>
          <span>Записаться</span>
        </div>
        <div class="action-item" @click="$router.push('/appointments')">
          <div class="icon-circle"><van-icon name="orders-o" size="24" /></div>
          <span>История</span>
        </div>
        <!-- Перекидываем на вкладку сертификатов -->
        <div class="action-item" @click="$router.push({ path: '/bonuses', query: { tab: 'certificates' } })">
          <div class="icon-circle"><van-icon name="coupon-o" size="24" /></div>
          <span>Сертификаты</span>
        </div>
      </div>
    </div>

    <!-- Нижняя навигация -->
    <BottomTabbar />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'
import BottomTabbar from '@/components/BottomTabbar.vue'

const authStore = useAuthStore()

const user = computed(() => authStore.user)
const userName = computed(() => {
  if (!user.value?.name) return 'Гость'
  return user.value.name.split(' ')[0]
})

const loading = ref(true)
const nextAppointment = ref<any>(null)

// Загрузка ближайшей записи
async function fetchNextAppointment() {
  try {
    const { data } = await apiClient.get('/appointments/')
    if (data.upcoming && data.upcoming.length > 0) {
      nextAppointment.value = data.upcoming[0]
    }
  } catch (error) {
    console.error('Ошибка загрузки записей:', error)
  } finally {
    loading.value = false
  }
}

function getServicesText(appt: any) {
  return appt.services.map((s: any) => s.name).join(', ')
}

function formatDate(dateStr: string, format: string) {
  const d = new Date(dateStr)
  if (format === 'DD') return d.getDate().toString().padStart(2, '0')
  if (format === 'MMM') {
    const months = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
    return months[d.getMonth()]
  }
  if (format === 'HH:mm') {
    return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  }
  return dateStr
}

onMounted(async () => {
  await authStore.fetchMe()
  await fetchNextAppointment()
})
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  padding: 24px 16px 80px 16px;
  background-color: var(--bg-light, #fef9f7);
  font-family: 'Inter', sans-serif;
}

/* Хедер */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  margin-top: 10px;
}

.greeting h1 {
  font-size: 22px;
  font-weight: 700;
  margin: 0 0 4px 0;
  color: var(--text-dark, #2d2a28);
}

.greeting p {
  margin: 0;
  font-size: 13px;
  color: var(--text-gray, #6b5f5a);
}

/* Аватарка */
.avatar-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar {
  width: 48px;
  height: 48px;
  background-color: #fff;
  border: 2px solid var(--primary, #f2a6b0);
  color: var(--primary, #f2a6b0);
  font-weight: 700;
  font-size: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-img {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid var(--primary, #f2a6b0);
}

/* Секции */
.section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-dark, #2d2a28);
  margin-bottom: 12px;
  margin-left: 4px;
}

/* Карточка ближайшей записи */
.appointment-card {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  display: flex;
  align-items: center;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
  cursor: pointer;
  transition: transform 0.2s;
}

.appointment-card:active {
  transform: scale(0.98);
}

.appt-date {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #fff0f2;
  color: #d85c6b;
  width: 56px;
  height: 56px;
  border-radius: 12px;
  margin-right: 16px;
}

.appt-date .day {
  font-size: 20px;
  font-weight: 700;
  line-height: 1;
}

.appt-date .month {
  font-size: 11px;
  text-transform: uppercase;
  font-weight: 600;
}

.appt-info {
  flex: 1;
}

.appt-time {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-dark, #2d2a28);
  margin-bottom: 4px;
}

.appt-services {
  font-size: 13px;
  color: var(--text-gray, #6b5f5a);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
}

.appt-arrow {
  color: #ccc;
}

.loading-block, .empty-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  text-align: center;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
}

.empty-card p {
  color: var(--text-gray, #6b5f5a);
  margin-bottom: 16px;
  font-size: 14px;
}

/* Карточка бонусов */
.bonus-card {
  background: linear-gradient(135deg, #ffffff 0%, #fff5f7 100%);
  border: 1px solid #f9d1d6;
  border-radius: 16px;
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
}

.bonus-info {
  display: flex;
  flex-direction: column;
}

.bonus-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-dark, #2d2a28);
  line-height: 1.2;
}

.bonus-label {
  font-size: 13px;
  color: var(--text-gray, #6b5f5a);
}

/* Быстрые действия */
.quick-actions {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.action-item {
  flex: 1;
  background: #fff;
  padding: 16px 8px;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
  cursor: pointer;
}

.icon-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #fff0f2;
  color: #d85c6b;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

.action-item span {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-dark, #2d2a28);
  text-align: center;
}

.brand-btn {
  background-color: var(--primary, #f2a6b0);
  border-color: var(--primary, #f2a6b0);
}
</style>