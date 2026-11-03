<template>
  <div class="review-page">
    <div class="page-header">
      <van-icon name="arrow-left" size="24" @click="$router.back()" />
      <h1>Отзыв об услуге</h1>
      <div style="width: 24px"></div>
    </div>

    <div v-if="loading" class="loading-center">
      <van-loading color="#f2a6b0" />
    </div>

    <div v-else-if="booking" class="form-container">
      <div class="header-info">
        <h2>Как прошел визит?</h2>
        <p>{{ booking.date }} • {{ booking.services.join(', ') }}</p>
      </div>

      <div class="rating-box">
        <van-rate v-model="rating" size="32" color="#f2a6b0" void-color="#e5e7eb" />
      </div>

      <van-field
        v-model="text"
        rows="4"
        type="textarea"
        placeholder="Что вам понравилось? (необязательно)"
        class="custom-textarea"
      />

      <van-button block round type="primary" class="brand-btn" @click="submit" :loading="submitting" :disabled="!rating">
        Отправить отзыв
      </van-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showSuccessToast, showFailToast } from 'vant'
import apiClient from '@/api/client'

const route = useRoute()
const router = useRouter()
const token = route.params.token

const loading = ref(true)
const booking = ref<any>(null)
const rating = ref(5)
const text = ref('')
const submitting = ref(false)

async function fetchBooking() {
  try {
    const { data } = await apiClient.get(`/reviews/${token}/`)
    booking.value = data
  } catch (e) {
    showFailToast('Ссылка недействительна или отзыв уже оставлен')
    router.push('/appointments')
  } finally {
    loading.value = false
  }
}

async function submit() {
  submitting.value = true
  try {
    await apiClient.post(`/reviews/${token}/submit/`, { rating: rating.value, text: text.value })
    showSuccessToast('Спасибо за ваш отзыв!')
    router.push('/appointments')
  } catch (e: any) {
    showFailToast(e.response?.data?.error || 'Ошибка отправки')
  } finally {
    submitting.value = false
  }
}

onMounted(() => fetchBooking())
</script>

<style scoped>
.review-page { min-height: 100vh; background-color: var(--bg-light, #fef9f7); padding: 24px 20px; font-family: 'Inter', sans-serif; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; }
.page-header h1 { font-size: 20px; font-weight: 700; margin: 0; }
.header-info { text-align: center; margin-bottom: 24px; }
.header-info h2 { font-size: 22px; font-weight: 700; color: #2d2a28; margin-bottom: 8px; }
.header-info p { font-size: 14px; color: #6b5f5a; }
.rating-box { display: flex; justify-content: center; margin-bottom: 24px; }
.custom-textarea { background: #fff; border-radius: 12px; margin-bottom: 24px; border: 1px solid #e5e7eb; }
.brand-btn { background-color: #f2a6b0; border-color: #f2a6b0; padding: 14px; font-weight: 600; }
.loading-center { display: flex; justify-content: center; padding: 40px; }
</style>