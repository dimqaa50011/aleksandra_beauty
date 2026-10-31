<template>
  <div class="booking-page">
    <div class="page-header">
      <van-icon name="arrow-left" size="24" class="back-icon" @click="goBack" />
      <h1>Онлайн-запись</h1>
      <div class="header-spacer"></div> <!-- Для центрирования заголовка -->
    </div>

    <div class="form-container">
      <!-- 1. КАТЕГОРИЯ -->
      <div class="form-group">
        <label class="form-label">Категория</label>
        <select v-model="selectedCategory" class="custom-select">
          <option disabled value="">Выберите категорию</option>
          <option v-for="cat in categories" :key="cat.id" :value="cat.id">
            {{ cat.name }}
          </option>
        </select>
      </div>

      <!-- 2. ДОБАВИТЬ УСЛУГУ -->
      <div class="form-group" v-if="selectedCategory">
        <label class="form-label">Добавить услугу</label>
        <div class="add-service-row">
          <select v-model="serviceToAdd" class="custom-select" style="flex: 1;">
            <option value="" disabled>Выберите услугу для добавления</option>
            <option v-for="srv in availableServices" :key="srv.id" :value="srv.id">
              {{ srv.name }} ({{ srv.duration }} мин) - {{ srv.price }} ₽
            </option>
          </select>
          <button class="btn-add" @click="addService" :disabled="!serviceToAdd">
            + Добавить
          </button>
        </div>
      </div>

      <!-- 3. ВЫБРАННЫЕ УСЛУГИ -->
      <div class="selected-services-box" v-if="selectedServices.length > 0">
        <div class="box-title">Выбранные услуги:</div>
        <div v-for="(srv, index) in selectedServices" :key="srv.id" class="selected-item">
          <span class="srv-name">{{ srv.name }} ({{ srv.duration }} мин)</span>
          <div class="srv-right">
            <span class="srv-price">{{ srv.price }} ₽</span>
            <span class="srv-remove" @click="removeService(index)">✕</span>
          </div>
        </div>
        <div class="totals-row">
          <span class="total-duration">⏱ Итого время: {{ totalDuration }} мин</span>
          <span class="total-price">🔥 Итого цена: {{ totalPrice }} ₽</span>
        </div>
      </div>

      <!-- 4. ДАТА И ВРЕМЯ -->
      <div class="datetime-row">
        <div class="form-group half">
          <label class="form-label">Дата *</label>
          <input 
            type="date" 
            v-model="selectedDate" 
            :min="todayStr" 
            class="custom-input"
          />
        </div>
        <div class="form-group half">
          <label class="form-label">Время *</label>
          <select v-model="selectedTime" class="custom-select" :disabled="!slots.length">
            <option value="" disabled>
              {{ !selectedDate || !selectedServices.length ? 'Сначала выберите услуги и дату' : (loadingSlots ? 'Загрузка...' : (slots.length === 0 ? 'Нет свободного времени' : 'Выберите время')) }}
            </option>
            <option v-for="time in slots" :key="time" :value="time">
              {{ time }}
            </option>
          </select>
          <div class="help-text" v-if="!selectedDate || !selectedServices.length">Выберите услуги и дату</div>
        </div>
      </div>

      <!-- 5. СОГЛАСИЕ -->
      <div class="consent-row">
        <input type="checkbox" id="consent" v-model="consentPd" class="custom-checkbox" />
        <label for="consent" class="consent-label">
          Я согласен на обработку персональных данных в соответствии с <a href="#">Политикой конфиденциальности</a>
        </label>
      </div>

      <!-- 6. КНОПКА -->
      <button 
        class="submit-btn" 
        :class="{ disabled: !isReadyToBook }"
        :disabled="!isReadyToBook || submitting"
        @click="onSubmit"
      >
        {{ submitting ? 'Записываем...' : 'Записаться' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { showSuccessToast, showFailToast } from 'vant'
import dayjs from 'dayjs'
import apiClient from '@/api/client'

const router = useRouter()

// Данные
const services = ref<any[]>([])
const categories = ref<{id: number, name: string}[]>([])
const selectedCategory = ref<number | ''>('')
const serviceToAdd = ref<number | ''>('')
const selectedServices = ref<any[]>([])

// Дата и время
const todayStr = dayjs().format('YYYY-MM-DD')
const selectedDate = ref<string>('')
const slots = ref<string[]>([])
const selectedTime = ref<string>('')
const loadingSlots = ref(false)

// Согласие
const consentPd = ref(false)
const submitting = ref(false)

// Вычисляемые
const availableServices = computed(() => {
  if (!selectedCategory.value) return []
  const catId = selectedCategory.value
  const selectedIds = selectedServices.value.map(s => s.id)
  return services.value.filter(s => s.category_id === catId && !selectedIds.includes(s.id))
})

const totalPrice = computed(() => selectedServices.value.reduce((sum, s) => sum + Number(s.price), 0))
const totalDuration = computed(() => selectedServices.value.reduce((sum, s) => sum + Number(s.duration), 0))
const isReadyToBook = computed(() => selectedServices.value.length > 0 && selectedDate.value && selectedTime.value && consentPd.value)

// Методы
function goBack() {
  router.back()
}

async function fetchServices() {
  try {
    const { data } = await apiClient.get('/services/')
    services.value = data.services
    
    const cats = new Map()
    services.value.forEach(s => {
      if (s.category_id && !cats.has(s.category_id)) {
        cats.set(s.category_id, { id: s.category_id, name: s.category_name })
      }
    })
    categories.value = Array.from(cats.values())
  } catch (error) {
    showFailToast('Не удалось загрузить услуги')
  }
}

function addService() {
  if (!serviceToAdd.value) return
  const srv = services.value.find(s => s.id === serviceToAdd.value)
  if (srv) {
    selectedServices.value.push(srv)
    serviceToAdd.value = ''
  }
}

function removeService(index: number) {
  selectedServices.value.splice(index, 1)
}

async function fetchSlots() {
  if (!selectedDate.value || selectedServices.value.length === 0) {
    slots.value = []
    selectedTime.value = ''
    return
  }
  
  loadingSlots.value = true
  selectedTime.value = ''
  
  try {
    const ids = selectedServices.value.map(s => s.id).join(',')
    const { data } = await apiClient.get(`/slots/?date=${selectedDate.value}&service_ids=${ids}`)
    slots.value = data.times || []
  } catch (error) {
    slots.value = []
  } finally {
    loadingSlots.value = false
  }
}

async function onSubmit() {
  if (!isReadyToBook.value) return
  submitting.value = true
  
  try {
    const datetimeStr = dayjs(`${selectedDate.value} ${selectedTime.value}`).format()
    const ids = selectedServices.value.map(s => s.id)
    
    await apiClient.post('/appointments/', {
      service_ids: ids,
      appointment_datetime: datetimeStr
    })
    
    showSuccessToast('Вы успешно записаны!')
    router.push('/')
  } catch (error: any) {
    const msg = error.response?.data?.appointment_datetime?.[0] || 'Ошибка записи'
    showFailToast(msg)
  } finally {
    submitting.value = false
  }
}

// Следим за изменениями
watch([selectedDate, selectedServices], fetchSlots, { deep: true })

onMounted(() => {
  fetchServices()
})
</script>

<style scoped>
.booking-page {
  min-height: 100vh;
  background-color: #ffffff;
  padding: 24px 20px 60px;
  font-family: 'Inter', sans-serif;
}

/* Обновленный хедер с кнопкой назад */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 32px;
  margin-top: 10px;
  padding: 0 4px;
}

.back-icon {
  cursor: pointer;
  color: var(--text-dark, #2d2a28);
  transition: opacity 0.2s;
}

.back-icon:active {
  opacity: 0.5;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-dark, #2d2a28);
  margin: 0;
  text-align: center;
}

.header-spacer {
  width: 24px;
}

.form-container {
  max-width: 500px;
  margin: 0 auto;
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-dark, #2d2a28);
  margin-bottom: 8px;
}

.custom-select,
.custom-input {
  width: 100%;
  padding: 12px 16px;
  font-size: 15px;
  font-family: inherit;
  color: var(--text-dark, #2d2a28);
  background-color: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  outline: none;
  appearance: none;
  box-sizing: border-box;
}

.custom-select {
  background-image: url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%232d2a28%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E");
  background-repeat: no-repeat;
  background-position: right 16px top 50%;
  background-size: 10px auto;
}

.custom-select:disabled,
.custom-input:disabled {
  background-color: #f9fafb;
  color: #9ca3af;
}

.custom-select:focus,
.custom-input:focus {
  border-color: var(--primary, #f2a6b0);
}

.add-service-row {
  display: flex;
  gap: 8px;
}

.btn-add {
  background-color: #7a6e6a;
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}

.btn-add:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.selected-services-box {
  border: 1px solid #d1d5db;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 20px;
  background-color: #fafafa;
}

.box-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-gray, #6b5f5a);
  margin-bottom: 12px;
}

.selected-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #e5e7eb;
  font-size: 14px;
}

.selected-item:last-child {
  border-bottom: none;
}

.srv-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.srv-remove {
  color: #ef4444;
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
}

.totals-row {
  display: flex;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #d1d5db;
  font-size: 14px;
  font-weight: 600;
}

.datetime-row {
  display: flex;
  gap: 12px;
}

.half {
  flex: 1;
}

.help-text {
  font-size: 12px;
  color: var(--text-gray, #6b5f5a);
  margin-top: 4px;
}

.consent-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 24px 0;
}

.custom-checkbox {
  margin-top: 2px;
  width: 18px;
  height: 18px;
  accent-color: var(--primary, #f2a6b0);
}

.consent-label {
  font-size: 13px;
  color: var(--text-gray, #6b5f5a);
  line-height: 1.4;
}

.consent-label a {
  color: var(--primary, #f2a6b0);
  text-decoration: underline;
}

.submit-btn {
  width: 100%;
  padding: 16px;
  background-color: var(--primary, #f2a6b0);
  color: white;
  border: none;
  border-radius: 60px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 15px rgba(242, 166, 176, 0.3);
}

.submit-btn.disabled {
  background-color: #f2a6b0;
  opacity: 0.5;
  box-shadow: none;
  cursor: not-allowed;
}

.submit-btn:active:not(.disabled) {
  transform: translateY(2px);
  background-color: var(--primary-hover, #e8919c);
}
</style>