<template>
  <div class="appointments-page">
    <div class="page-header">
      <h1>Мои визиты</h1>
    </div>

    <van-tabs v-model:active="activeTab" color="#f2a6b0" title-active-color="#2d2a28" title-inactive-color="#6b5f5a" sticky offset-top="0">
      
      <!-- ВКЛАДКА: ПРЕДСТОЯЩИЕ -->
      <van-tab title="Предстоящие">
        <div v-if="loading" class="loading-center">
          <van-loading color="#f2a6b0">Загружаем...</van-loading>
        </div>
        
        <div v-else-if="upcoming.length === 0" class="empty-state">
          <van-icon name="calendar-o" size="48" color="#d1d5db" />
          <p>У вас нет запланированных визитов</p>
          <van-button round type="primary" class="brand-btn" to="/booking">
            Записаться
          </van-button>
        </div>

        <div v-else class="list-container">
          <div v-for="appt in upcoming" :key="appt.id" class="appt-card">
            <div class="card-header">
              <div class="date-badge">
                <span class="day">{{ formatDate(appt.appointment_datetime, 'DD') }}</span>
                <span class="month">{{ formatDate(appt.appointment_datetime, 'MMM') }}</span>
              </div>
              <div class="header-info">
                <div class="time">{{ formatDate(appt.appointment_datetime, 'HH:mm') }}</div>
                <div class="status-badge" :class="appt.status">
                  {{ appt.status === 'pending' ? 'Ждет подтверждения' : 'Подтверждено' }}
                </div>
              </div>
            </div>
            
            <div class="card-body">
              <div class="services-list">
                <div v-for="srv in appt.services" :key="srv.id" class="service-item">
                  • {{ srv.name }}
                </div>
              </div>
              <div class="price-row">
                <span>Итого:</span>
                <strong>{{ appt.total_price }} ₽</strong>
              </div>
            </div>

            <div class="card-footer" v-if="appt.can_cancel">
              <van-button plain round block type="danger" size="small" @click="openCancelSheet(appt)">
                Отменить запись
              </van-button>
            </div>
          </div>
        </div>
      </van-tab>

      <!-- ВКЛАДКА: ИСТОРИЯ -->
      <van-tab title="История">
        <div v-if="loading" class="loading-center">
          <van-loading color="#f2a6b0">Загружаем...</van-loading>
        </div>

        <div v-else-if="past.length === 0" class="empty-state">
          <p>История визитов пуста</p>
        </div>

        <div v-else class="list-container">
          <div v-for="appt in past" :key="appt.id" class="appt-card past-card">
            <div class="card-header">
              <div class="date-badge gray">
                <span class="day">{{ formatDate(appt.appointment_datetime, 'DD') }}</span>
                <span class="month">{{ formatDate(appt.appointment_datetime, 'MMM') }}</span>
              </div>
              <div class="header-info">
                <div class="time">{{ formatDate(appt.appointment_datetime, 'HH:mm') }}</div>
                <div class="status-badge" :class="appt.status">
                  {{ appt.status === 'completed' ? 'Выполнено' : (appt.status === 'cancelled' ? 'Отменено' : 'Не пришли') }}
                </div>
              </div>
            </div>
            
            <div class="card-body">
              <div class="services-list">
                <div v-for="srv in appt.services" :key="srv.id" class="service-item">
                  {{ srv.name }}
                </div>
              </div>
              
              <!-- Если визит состоялся и есть токен для отзыва -->
              <div class="review-action" v-if="appt.status === 'completed' && appt.review_token">
                <van-button round block size="small" color="#fff0f2" style="color: #d85c6b;" @click="goToReview(appt.review_token)">
                  ⭐ Оставить отзыв
                </van-button>
              </div>
            </div>
          </div>
        </div>
      </van-tab>
    </van-tabs>

    <!-- Шторка отмены -->
    <van-action-sheet
      v-model:show="showCancelSheet"
      :actions="cancelReasons"
      cancel-text="Закрыть"
      description="Пожалуйста, укажите причину отмены:"
      close-on-click-action
      @select="onSelectReason"
    />

    <BottomTabbar />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { showSuccessToast, showFailToast } from 'vant'
import apiClient from '@/api/client'
import BottomTabbar from '@/components/BottomTabbar.vue'

const activeTab = ref(0)
const loading = ref(true)
const upcoming = ref<any[]>([])
const past = ref<any[]>([])

// Отмена
const showCancelSheet = ref(false)
const appointmentToCancel = ref<any>(null)
const cancelReasons = [
  { name: 'Болею', value: 'sick' },
  { name: 'Планы изменились', value: 'plans_changed' },
  { name: 'Не смогу прийти', value: 'cant_make_it' },
  { name: 'Другое', value: 'other' },
]

async function fetchAppointments() {
  loading.value = true
  try {
    const { data } = await apiClient.get('/appointments/')
    upcoming.value = data.upcoming
    past.value = data.past
  } catch (error) {
    showFailToast('Не удалось загрузить записи')
  } finally {
    loading.value = false
  }
}

// Отмена записи
function openCancelSheet(appt: any) {
  appointmentToCancel.value = appt
  showCancelSheet.value = true
}

async function onSelectReason(action: any) {
  if (!appointmentToCancel.value) return
  
  try {
    // Отправляем DELETE запрос с причиной в query params
    await apiClient.delete(`/appointments/${appointmentToCancel.value.id}/`, {
      params: { 
        reason: action.value,
        reason_text: action.value === 'other' ? 'Клиент указал Другое' : ''
      }
    })
    
    showSuccessToast('Запись отменена')
    // Обновляем список
    await fetchAppointments()
  } catch (error: any) {
    const msg = error.response?.data?.detail || 'Не удалось отменить запись'
    showFailToast(msg)
  }
}

// Переход на страницу отзыва (пока ведем на старую HTML форму Django)
function goToReview(token: string) {
  // Предполагается, что форма отзыва на бэкенде доступна по этому адресу
  window.location.href = `https://sasha-sugar.ru/review/${token}/`
}

// Форматирование даты (без dayjs)
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

onMounted(() => {
  fetchAppointments()
})
</script>

<style scoped>
.appointments-page {
  min-height: 100vh;
  padding-bottom: 80px; /* Для таббара */
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
  color: var(--text-dark, #2d2a28);
}

/* Стилизация вкладок Vant */
:deep(.van-tabs__wrap) {
  background: var(--bg-light, #fef9f7);
}
:deep(.van-tabs__nav) {
  background: transparent;
}
:deep(.van-tab) {
  font-size: 15px;
  font-weight: 500;
}
:deep(.van-tabs__line) {
  border-radius: 2px;
}

/* Контейнер списка */
.list-container {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Карточка записи */
.appt-card {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
  border: 1px solid #f0e8e5;
}

.past-card {
  opacity: 0.8;
}

.card-header {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px dashed #e5e7eb;
}

.date-badge {
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

.date-badge.gray {
  background: #f3f4f6;
  color: #6b7280;
}

.date-badge .day {
  font-size: 20px;
  font-weight: 700;
  line-height: 1;
}

.date-badge .month {
  font-size: 11px;
  text-transform: uppercase;
  font-weight: 600;
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.time {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-dark, #2d2a28);
}

.status-badge {
  font-size: 12px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
  display: inline-block;
  width: fit-content;
}

.status-badge.pending {
  background: #fef3c7;
  color: #d97706;
}

.status-badge.confirmed {
  background: #dcfce7;
  color: #16a34a;
}

.status-badge.completed {
  background: #e0e7ff;
  color: #4338ca;
}

.status-badge.cancelled,
.status-badge.no_show {
  background: #fee2e2;
  color: #dc2626;
}

.card-body {
  margin-bottom: 12px;
}

.services-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.service-item {
  font-size: 14px;
  color: var(--text-dark, #2d2a28);
}

.price-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: var(--text-gray, #6b5f5a);
  padding-top: 12px;
  border-top: 1px solid #f3f4f6;
}

.price-row strong {
  color: var(--text-dark, #2d2a28);
  font-size: 16px;
}

.card-footer {
  margin-top: 16px;
}

.review-action {
  margin-top: 12px;
}

/* Пустые состояния и лоадеры */
.empty-state {
  padding: 60px 20px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.empty-state p {
  color: var(--text-gray, #6b5f5a);
  font-size: 14px;
  margin: 0;
}

.loading-center {
  display: flex;
  justify-content: center;
  padding: 40px;
}

.brand-btn {
  background-color: var(--primary, #f2a6b0);
  border-color: var(--primary, #f2a6b0);
  padding: 0 32px;
}
</style>