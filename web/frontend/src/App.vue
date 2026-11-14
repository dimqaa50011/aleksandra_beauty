<template>
  <router-view />
  
  <!-- Модалка, если нужно ввести телефон (для юзеров из соцсетей) -->
  <van-dialog
    v-model:show="authStore.needsPhone"
    title="Подтвердите номер"
    :show-cancel-button="false"
    :close-on-click-overlay="false"
  >
    <div style="padding: 20px;">
      <p style="margin-bottom: 16px; font-size: 14px;">
        Чтобы мы могли записывать вас на услуги и начислять бонусы, пожалуйста, укажите свой номер телефона.
      </p>
      
      <van-field
        v-model="phone"
        label="Телефон"
        placeholder="+7 (999) 123-45-67"
        type="tel"
      />
      
      <van-button 
        type="primary" 
        block 
        round 
        style="margin-top: 16px;"
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

const authStore = useAuthStore()
const phone = ref('')
const saving = ref(false)

async function savePhone() {
  if (!phone.value) return
  saving.value = true
  try {
    // Отправляем телефон на бэкенд, чтобы он привязался к текущему CabinetUser
    await apiClient.patch('/me/phone/', { phone: phone.value })
    await authStore.fetchMe()
    authStore.needsPhone = false
    showSuccessToast('Телефон привязан!')
  } catch (e: any) {
    showFailToast(e.response?.data?.error || 'Ошибка привязки телефона')
  } finally {
    saving.value = false
  }
}
</script>