<template>
  <router-view />
  
  <!-- Модалка для подтверждения телефона (для новых юзеров из соцсетей) -->
  <van-dialog
    v-model:show="authStore.needsPhone"
    title="Подтвердите номер"
    :show-cancel-button="false"
    :show-confirm-button="false"
    :close-on-click-overlay="false"
  >
    <div style="padding: 20px;">
      <p style="margin-bottom: 16px; font-size: 14px; color: #6b5f5a; line-height: 1.5;">
        Чтобы мы могли записывать вас на услуги и начислять бонусы, пожалуйста, укажите свой номер телефона.
      </p>
      
      <van-field
        v-model="phone"
        @update:model-value="(val) => (phone = formatPhone(val))"  
        label="Телефон"
        placeholder="+7 (999) 123-45-67"
        type="tel"
        :border="false"
        style="background: #f9fafb; border-radius: 8px;"
      />
      
      <van-button 
        type="primary" 
        block 
        round 
        style="margin-top: 20px; background-color: #2b8cf6; border-color: #2b8cf6;"
        :loading="saving"
        @click="savePhone"
      >
        Подтвердить
      </van-button>
    </div>
  </van-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { showSuccessToast, showFailToast } from 'vant'
import apiClient from '@/api/client'
import { formatPhone } from '@/utils/phone'

const authStore = useAuthStore()
const phone = ref('')
const saving = ref(false)

async function savePhone() {
  if (!phone.value) return
  saving.value = true
  try {
    // Отправляем телефон на бэкенд (в BindPhoneView)
    await apiClient.patch('/me/phone/', { phone: phone.value })
    
    // Обновляем профиль в сторе, чтобы получить актуальные данные
    await authStore.fetchMe()
    
    // Закрываем модалку
    authStore.needsPhone = false
    phone.value = ''
    showSuccessToast('Телефон успешно привязан!')
  } catch (e: any) {
    showFailToast(e.response?.data?.error || 'Ошибка привязки телефона')
  } finally {
    saving.value = false
  }
}
</script>

<style>
/* Глобальные стили, если нужны */
body {
  margin: 0;
  background-color: #f7f8fa;
}
</style>