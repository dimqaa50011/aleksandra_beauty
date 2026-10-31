<template>
  <div class="bonuses-page">
    <div class="page-header">
      <h1>Бонусы и подарки</h1>
    </div>

    <!-- ГЛАВНАЯ КАРТОЧКА БАЛАНСА -->
    <div class="balance-card">
      <div class="balance-info">
        <span class="balance-label">Ваш баланс</span>
        <div class="balance-value">
          {{ bonuses?.balance || 0 }} <span class="currency">б.</span>
        </div>
      </div>
      <div class="balance-limit">
        <van-icon name="info-o" />
        Можно списать до {{ bonuses?.max_spend_percent || 15 }}% от чека
      </div>
    </div>

    <van-tabs v-model:active="activeTab" color="#f2a6b0" title-active-color="#2d2a28" title-inactive-color="#6b5f5a">
      
      <!-- ВКЛАДКА 1: ИСТОРИЯ БОНУСОВ -->
      <van-tab title="История">
        <div v-if="loading" class="loading-center">
          <van-loading color="#f2a6b0">Загружаем...</van-loading>
        </div>
        
        <div v-else-if="!bonuses?.transactions?.length" class="empty-state">
          <p>У вас пока нет начислений бонусов.</p>
        </div>

        <div v-else class="list-container">
          <!-- Активный кэшбэк -->
          <div class="cashback-section" v-if="bonuses?.cashback_rules?.length">
            <div class="section-title">Сейчас кэшбэк на:</div>
            <div class="cashback-list">
              <div v-for="rule in bonuses.cashback_rules" :key="rule.id" class="cashback-item">
                <span class="c-name">{{ rule.service_name }}</span>
                <span class="c-percent">{{ Number(rule.percent) }}%</span>
              </div>
            </div>
          </div>

          <div class="section-title" style="margin-top: 24px;">История операций</div>
          <div v-for="tx in bonuses.transactions" :key="tx.id" class="tx-item">
            <div class="tx-icon" :class="tx.amount > 0 ? 'plus' : 'minus'">
              <van-icon :name="tx.amount > 0 ? 'plus' : 'minus'" />
            </div>
            <div class="tx-info">
              <div class="tx-reason">{{ tx.reason_display }}</div>
              <div class="tx-date">{{ formatDate(tx.created_at) }}</div>
            </div>
            <div class="tx-amount" :class="tx.amount > 0 ? 'text-green' : 'text-gray'">
              {{ tx.amount > 0 ? '+' : '' }}{{ tx.amount }}
            </div>
          </div>
        </div>
      </van-tab>

      <!-- ВКЛАДКА 2: СЕРТИФИКАТЫ -->
      <van-tab title="Сертификаты">
        <div v-if="loadingCerts" class="loading-center">
          <van-loading color="#f2a6b0" />
        </div>
        
        <div v-else-if="!certificates.length" class="empty-state">
          <p>У вас нет сертификатов.</p>
        </div>

        <div v-else class="list-container">
          <div v-for="cert in certificates" :key="cert.id" class="cert-card" :class="{ 'is-used': !cert.is_available }">
            <div class="cert-header">
              <div class="cert-price">{{ cert.price }} ₽</div>
              <div class="cert-status" :class="cert.is_available ? 'active' : 'inactive'">
                {{ cert.status_display }}
              </div>
            </div>
            <div class="cert-code">Код: {{ cert.code }}</div>
            <div class="cert-expire">Действует до: {{ formatDate(cert.expire_date) }}</div>
          </div>
        </div>
      </van-tab>

      <!-- ВКЛАДКА 3: РЕФЕРАЛКА -->
      <van-tab title="Пригласить друга">
        <div v-if="loadingRef" class="loading-center">
          <van-loading color="#f2a6b0" />
        </div>
        
        <div v-else class="referral-container">
          <div class="ref-hero">
            <van-icon name="gift-o" size="48" color="#f2a6b0" />
            <h2>Дарите красоту и получайте бонусы!</h2>
            <p>Отправьте ссылку подруге. Когда она зарегистрируется, вы обе получите бонусы. А после её первого визита — еще больше!</p>
          </div>

          <div class="ref-link-box">
            <input type="text" readonly :value="referral?.link" class="ref-input" />
            <button class="btn-copy" @click="copyLink">Копировать</button>
          </div>

          <div class="ref-stats">
            <div class="stat-item">
              <span class="stat-value">{{ referral?.invited_count || 0 }}</span>
              <span class="stat-label">Пришло друзей</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ referral?.rewarded_count || 0 }}</span>
              <span class="stat-label">Бонусы начислены</span>
            </div>
          </div>

          <div class="ref-list" v-if="referral?.referrals?.length">
            <div class="section-title">Ваши друзья</div>
            <div v-for="(ref, i) in referral.referrals" :key="i" class="ref-friend">
              <span>{{ ref.name }}</span>
              <span class="ref-status">{{ ref.status }}</span>
            </div>
          </div>
        </div>
      </van-tab>

    </van-tabs>

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
const loadingCerts = ref(true)
const loadingRef = ref(true)

const bonuses = ref<any>(null)
const certificates = ref<any[]>([])
const referral = ref<any>(null)

async function fetchBonuses() {
  try {
    const { data } = await apiClient.get('/bonuses/')
    bonuses.value = data
  } catch (error) {
    showFailToast('Не удалось загрузить бонусы')
  } finally {
    loading.value = false
  }
}

async function fetchCertificates() {
  try {
    const { data } = await apiClient.get('/certificates/')
    certificates.value = data.certificates
  } catch (error) {
    console.error(error)
  } finally {
    loadingCerts.value = false
  }
}

async function fetchReferral() {
  try {
    const { data } = await apiClient.get('/referral/')
    referral.value = data
  } catch (error) {
    console.error(error)
  } finally {
    loadingRef.value = false
  }
}

function copyLink() {
  if (!referral.value?.link) return
  navigator.clipboard.writeText(referral.value.link)
    .then(() => showSuccessToast('Ссылка скопирована!'))
    .catch(() => showFailToast('Не удалось скопировать'))
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getDate().toString().padStart(2, '0')}.${(d.getMonth() + 1).toString().padStart(2, '0')}.${d.getFullYear()}`
}

onMounted(() => {
  fetchBonuses()
  fetchCertificates()
  fetchReferral()
})
</script>

<style scoped>
.bonuses-page {
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
  color: var(--text-dark, #2d2a28);
}

/* Карточка баланса */
.balance-card {
  margin: 0 16px 16px;
  background: linear-gradient(135deg, #ffffff 0%, #fff0f2 100%);
  border: 1px solid #f9d1d6;
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 4px 15px rgba(242, 166, 176, 0.1);
  position: relative;
  overflow: hidden;
}

.balance-info {
  display: flex;
  flex-direction: column;
}

.balance-label {
  font-size: 14px;
  color: var(--text-gray, #6b5f5a);
  margin-bottom: 4px;
}

.balance-value {
  font-size: 36px;
  font-weight: 800;
  color: var(--text-dark, #2d2a28);
  line-height: 1;
}

.balance-value .currency {
  font-size: 20px;
  font-weight: 600;
  color: #d85c6b;
}

.balance-limit {
  margin-top: 16px;
  font-size: 12px;
  color: #d85c6b;
  background: rgba(255,255,255,0.6);
  padding: 6px 12px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

/* Общие стили */
:deep(.van-tabs__wrap) {
  background: transparent;
}
:deep(.van-tabs__nav) {
  background: transparent;
}
:deep(.van-tab) {
  font-size: 15px;
  font-weight: 500;
}

.list-container {
  padding: 16px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-dark, #2d2a28);
  margin-bottom: 12px;
}

/* Кэшбэк */
.cashback-section {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  border: 1px solid #f0e8e5;
}

.cashback-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.cashback-item {
  background: #fff0f2;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 13px;
  color: #d85c6b;
  display: flex;
  align-items: center;
  gap: 6px;
}

.c-percent {
  font-weight: 700;
}

/* История транзакций */
.tx-item {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f0e8e5;
}

.tx-item:last-child {
  border-bottom: none;
}

.tx-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
}

.tx-icon.plus {
  background: #dcfce7;
  color: #16a34a;
}

.tx-icon.minus {
  background: #fee2e2;
  color: #dc2626;
}

.tx-info {
  flex: 1;
}

.tx-reason {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-dark, #2d2a28);
  margin-bottom: 2px;
}

.tx-date {
  font-size: 12px;
  color: var(--text-gray, #6b5f5a);
}

.tx-amount {
  font-size: 16px;
  font-weight: 700;
}

.text-green { color: #16a34a; }
.text-gray { color: #6b5f5a; }

/* Сертификаты */
.cert-card {
  background: #fff;
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 12px;
  border: 1px solid #f9d1d6;
  box-shadow: 0 4px 15px rgba(0,0,0,0.02);
  position: relative;
  overflow: hidden;
}

.cert-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 6px;
  background: var(--primary, #f2a6b0);
}

.cert-card.is-used {
  opacity: 0.6;
  filter: grayscale(0.5);
}

.cert-card.is-used::before {
  background: #9ca3af;
}

.cert-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.cert-price {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-dark, #2d2a28);
}

.cert-status {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
}

.cert-status.active {
  background: #dcfce7;
  color: #16a34a;
}

.cert-status.inactive {
  background: #f3f4f6;
  color: #6b7280;
}

.cert-code {
  font-size: 14px;
  color: var(--text-gray, #6b5f5a);
  margin-bottom: 4px;
}

.cert-expire {
  font-size: 12px;
  color: var(--text-gray, #6b5f5a);
}

/* Рефералка */
.referral-container {
  padding: 16px;
}

.ref-hero {
  text-align: center;
  padding: 24px 16px;
}

.ref-hero h2 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-dark, #2d2a28);
  margin: 16px 0 8px;
}

.ref-hero p {
  font-size: 14px;
  color: var(--text-gray, #6b5f5a);
  line-height: 1.5;
}

.ref-link-box {
  display: flex;
  background: #fff;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  padding: 6px;
  margin-bottom: 24px;
}

.ref-input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 8px 12px;
  font-size: 14px;
  color: var(--text-dark, #2d2a28);
  outline: none;
}

.btn-copy {
  background: var(--primary, #f2a6b0);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}

.ref-stats {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.stat-item {
  flex: 1;
  background: #fff;
  padding: 16px;
  border-radius: 16px;
  text-align: center;
  box-shadow: 0 4px 15px rgba(0,0,0,0.02);
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-dark, #2d2a28);
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: var(--text-gray, #6b5f5a);
}

.ref-friend {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #f0e8e5;
  font-size: 14px;
}

.ref-friend:last-child {
  border-bottom: none;
}

.ref-status {
  color: #d85c6b;
  font-weight: 500;
}

/* Утилиты */
.loading-center {
  display: flex;
  justify-content: center;
  padding: 40px;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-gray, #6b5f5a);
  font-size: 14px;
}
</style>