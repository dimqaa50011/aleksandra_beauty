<template>
  <div class="cert-detail-page">
    <div class="page-header">
      <van-icon name="arrow-left" size="24" @click="$router.back()" />
      <h1>Сертификат</h1>
      <div style="width: 24px"></div>
    </div>

    <div v-if="loading" class="loading-center">
      <van-loading color="#f2a6b0" />
    </div>

    <div v-else-if="cert" class="cert-detail-container">
      
      <!-- КАРТОЧКА СЕРТИФИКАТА -->
      <div class="cert-ticket" :class="{ 'used': !cert.is_available }">
        <div class="ticket-header">
          <span class="brand">Sasha Sugar</span>
          <span class="price">{{ cert.price }} ₽</span>
        </div>
        
        <div class="ticket-body">
          <div class="status">{{ cert.status_display }}</div>
          <div class="code">Код: {{ cert.code }}</div>
          <div class="expire">Действует до: {{ formatDate(cert.expire_date) }}</div>
        </div>
        
        <div class="ticket-footer">
          Подарочный сертификат
        </div>
      </div>

      <!-- QR КОД -->
      <div class="qr-section" v-if="cert.qr_code">
        <h3>Покажите этот QR-код администратору</h3>
        <div class="qr-wrapper">
          <img :src="cert.qr_code" alt="QR-код сертификата" />
        </div>
      </div>
      <div class="qr-section" v-else>
        <p style="color: #ef4444; text-align: center;">QR-код для этого сертификата не был сгенерирован.</p>
      </div>

      <!-- ПОЛНЫЙ ТОКЕН (для ручного ввода) -->
      <div class="token-section">
        <p>Если сканер не работает, продиктуйте код:</p>
        <div class="token-box" @click="copyToken">
          <span>{{ cert.token }}</span>
          <van-icon name="description" />
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { showSuccessToast, showFailToast } from 'vant'
import apiClient from '@/api/client'

const route = useRoute()
const loading = ref(true)
const cert = ref<any>(null)

async function fetchCert() {
  try {
    const { data } = await apiClient.get(`/certificates/${route.params.id}/`)
    cert.value = data
  } catch (error) {
    showFailToast('Не удалось загрузить сертификат')
  } finally {
    loading.value = false
  }
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getDate().toString().padStart(2, '0')}.${(d.getMonth() + 1).toString().padStart(2, '0')}.${d.getFullYear()}`
}

function copyToken() {
  if (!cert.value?.token) return
  navigator.clipboard.writeText(cert.value.token)
    .then(() => showSuccessToast('Код скопирован!'))
}

onMounted(() => {
  fetchCert()
})
</script>

<style scoped>
.cert-detail-page {
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

/* Красивая карточка-билет */
.cert-ticket {
  background: linear-gradient(135deg, #f2a6b0 0%, #e8919c 100%);
  border-radius: 20px;
  color: white;
  padding: 24px;
  box-shadow: 0 10px 30px rgba(242, 166, 176, 0.4);
  position: relative;
  overflow: hidden;
  margin-bottom: 32px;
}

.cert-ticket.used {
  background: linear-gradient(135deg, #9ca3af 0%, #6b7280 100%);
  box-shadow: none;
  opacity: 0.8;
}

.ticket-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px dashed rgba(255,255,255,0.3);
  padding-bottom: 16px;
  margin-bottom: 16px;
}

.brand {
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.price {
  font-size: 28px;
  font-weight: 800;
}

.ticket-body {
  margin-bottom: 24px;
}

.status {
  display: inline-block;
  background: rgba(255,255,255,0.2);
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 12px;
}

.code {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
}

.expire {
  font-size: 13px;
  opacity: 0.8;
}

.ticket-footer {
  font-size: 12px;
  text-align: center;
  opacity: 0.6;
  border-top: 1px dashed rgba(255,255,255,0.3);
  padding-top: 16px;
}

/* QR */
.qr-section h3 {
  font-size: 16px;
  text-align: center;
  color: var(--text-dark, #2d2a28);
  margin-bottom: 16px;
}

.qr-wrapper {
  background: #fff;
  padding: 16px;
  border-radius: 20px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
  width: 240px;
  margin: 0 auto 32px;
}

.qr-wrapper img {
  width: 100%;
  height: auto;
  display: block;
}

/* Токен */
.token-section {
  text-align: center;
}

.token-section p {
  font-size: 13px;
  color: var(--text-gray, #6b5f5a);
  margin-bottom: 12px;
}

.token-box {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  padding: 12px 20px;
  border-radius: 12px;
  border: 1px solid #d1d5db;
  font-family: monospace;
  font-size: 14px;
  color: var(--text-dark, #2d2a28);
  cursor: pointer;
}

.loading-center {
  display: flex;
  justify-content: center;
  padding: 40px;
}
</style>