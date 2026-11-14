<template>
  <div class="login-page">
    <!-- ХЕДЕР (Логотип и приветствие) -->
    <div class="header">
      <div class="logo-circle">S</div>
      <h1 v-if="!isResetMode">С возвращением!</h1>
      <h1 v-else>Восстановление</h1>
      <p v-if="!isResetMode">Войдите в личный кабинет</p>
      <p v-else>Установите новый пароль по СМС</p>
    </div>

    <!-- ========================================== -->
    <!-- РЕЖИМ 1: ОБЫЧНЫЙ ВХОД                      -->
    <!-- ========================================== -->
    <van-form v-if="!isResetMode" @submit="onLoginSubmit" class="form-container">
      <van-cell-group inset class="custom-cell-group">
        <van-field
          v-model="phone"
          name="phone"
          label="Телефон"
          placeholder="+7 (999) 123-45-67"
          type="tel"
          :rules="[{ required: true, message: 'Введите телефон' }]"
          class="custom-field"
        />
        <van-field
          v-model="password"
          type="password"
          name="password"
          label="Пароль"
          placeholder="Минимум 8 символов"
          :rules="[{ required: true, message: 'Введите пароль' }]"
          class="custom-field"
        />
      </van-cell-group>

      <div class="submit-btn">
        <van-button 
          round block type="primary" native-type="submit" 
          :loading="loading" loading-text="Входим..." class="brand-btn"
        >
          Войти
        </van-button>
      </div>
    </van-form>

    <!-- ========================================== -->
    <!-- РЕЖИМ 2: УСТАНОВКА/СБРОС ПАРОЛЯ             -->
    <!-- ========================================== -->
    <div v-else class="form-container">
      <!-- Шаг 1: Ввод телефона -->
      <van-form v-if="resetStep === 1" @submit="requestResetCode">
        <p class="reset-desc">Введите номер телефона, привязанный к вашему аккаунту. Мы отправим код для входа.</p>
        
        <van-cell-group inset class="custom-cell-group">
          <van-field
            v-model="phone"
            name="phone"
            label="Телефон"
            placeholder="+7 (999) 123-45-67"
            type="tel"
            :rules="[{ required: true, message: 'Введите телефон' }]"
            class="custom-field"
          />
        </van-cell-group>

        <div class="submit-btn">
          <van-button round block type="primary" native-type="submit" :loading="resetLoading" class="brand-btn">
            Получить код
          </van-button>
        </div>
      </van-form>

      <!-- Шаг 2: Ввод кода из СМС и нового пароля -->
      <van-form v-else @submit="confirmResetPassword">
        <p class="reset-desc">Мы отправили код на номер <b>{{ phone }}</b>. Введите его и придумайте новый пароль.</p>

        <van-cell-group inset class="custom-cell-group">
          <van-field
            v-model="resetCode"
            name="code"
            label="Код из СМС"
            placeholder="123456"
            type="digit"
            maxlength="6"
            :rules="[{ required: true, message: 'Введите код из СМС' }]"
            class="custom-field"
          />
          <van-field
            v-model="newPassword"
            type="password"
            name="newPassword"
            label="Новый пароль"
            placeholder="Минимум 8 символов"
            :rules="[{ required: true, message: 'Введите пароль' }, { validator: (val) => val.length >= 8, message: 'Минимум 8 символов' }]"
            class="custom-field"
          />
          <van-field
            v-model="newPasswordConfirm"
            type="password"
            name="newPasswordConfirm"
            label="Повторите"
            placeholder="Повторите пароль"
            :rules="[{ required: true, message: 'Повторите пароль' }, { validator: validateConfirm, message: 'Пароли не совпадают' }]"
            class="custom-field"
          />
        </van-cell-group>

        <div class="submit-btn">
          <van-button round block type="primary" native-type="submit" :loading="resetLoading" class="brand-btn">
            Установить пароль и войти
          </van-button>
        </div>
      </van-form>
    </div>

    <!-- ССЫЛКИ ВНИЗУ -->
    <div class="links">
      <!-- Если в режиме логина -->
      <template v-if="!isResetMode">
        <router-link to="/register">У меня нет аккаунта</router-link>
        <span class="divider">•</span>
        <a href="#" @click.prevent="isResetMode = true">Забыли пароль?</a>
      </template>
      <!-- Если в режиме восстановления -->
      <template v-else>
        <a href="#" @click.prevent="isResetMode = false; resetStep = 1">← Вернуться к входу</a>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showFailToast, showSuccessToast } from 'vant'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'

const router = useRouter()
const authStore = useAuthStore()

// Состояния для обычного входа
const phone = ref('')
const password = ref('')
const loading = ref(false)

// Состояния для восстановления
const isResetMode = ref(false)
const resetStep = ref(1) // 1 = ввод телефона, 2 = ввод кода и пароля
const resetCode = ref('')
const newPassword = ref('')
const newPasswordConfirm = ref('')
const resetLoading = ref(false)

const validateConfirm = (val: string) => val === newPassword.value

// --- 1. ОБЫЧНЫЙ ВХОД ---
async function onLoginSubmit() {
  loading.value = true
  try {
    await authStore.login(phone.value, password.value)
    showSuccessToast('Успешный вход')
    router.push({ name: 'home' })
  } catch (error: any) {
    const data = error.response?.data
    
    // Если бэкенд вернул ошибку, что пароля нет — включаем режим сброса!
    if (data?.error_code === 'no_password') {
      showFailToast('Похоже, вы входили через соцсети. Установите пароль.')
      isResetMode.value = true
      resetStep.value = 1 // Начинаем с ввода телефона
    } else {
      const msg = data?.detail || data?.phone?.[0] || 'Неверный телефон или пароль'
      showFailToast(msg)
    }
  } finally {
    loading.value = false
  }
}

// --- 2. ЗАПРОС КОДА ---
async function requestResetCode() {
  resetLoading.value = true
  try {
    await apiClient.post('/auth/password/reset-request/', { phone: phone.value })
    showSuccessToast('Код отправлен по СМС')
    resetStep.value = 2 // Переходим к вводу кода
  } catch (error: any) {
    showFailToast('Ошибка отправки. Проверьте телефон.')
  } finally {
    resetLoading.value = false
  }
}

// --- 3. УСТАНОВКА ПАРОЛЯ И АВТОВХОД ---
async function confirmResetPassword() {
  resetLoading.value = true
  try {
    // Отправляем запрос на сброс пароля
    const { data } = await apiClient.post('/auth/password/reset-confirm/', {
      phone: phone.value,
      code: resetCode.value,
      new_password: newPassword.value
    })
    
    // Бэкенд возвращает access-токен! Авторизуем пользователя.
    authStore.setToken(data.access)
    await authStore.fetchMe()
    
    showSuccessToast('Пароль установлен!')
    router.push({ name: 'home' })
  } catch (error: any) {
    const msg = error.response?.data?.code?.[0] || error.response?.data?.error || 'Неверный код'
    showFailToast(msg)
  } finally {
    resetLoading.value = false
  }
}
</script>

<style scoped>
/* Используем стили, которые мы писали ранее */
.login-page {
  min-height: 100vh;
  padding: 40px 20px;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-light, #fef9f7);
  font-family: 'Inter', sans-serif;
}

.header {
  text-align: center;
  margin-bottom: 32px;
  margin-top: 20px;
}

.logo-circle {
  width: 64px;
  height: 64px;
  background-color: var(--primary, #f2a6b0);
  color: white;
  font-size: 32px;
  font-weight: bold;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px auto;
  box-shadow: 0 4px 20px rgba(242, 166, 176, 0.35);
}

h1 {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 8px 0;
  color: var(--text-dark, #2d2a28);
  letter-spacing: -0.5px;
}

.header p {
  margin: 0;
  color: var(--text-gray, #6b5f5a);
  font-size: 14px;
}

.form-container {
  margin-top: 16px;
}

.custom-cell-group {
  background: #ffffff;
  border-radius: 20px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
  overflow: hidden;
}

.custom-field {
  padding: 16px;
}

:deep(.van-field__label) {
  color: var(--text-gray, #6b5f5a);
  font-size: 14px;
  width: 80px;
}

:deep(.van-field__control) {
  color: var(--text-dark, #2d2a28);
  font-size: 16px;
}

.submit-btn {
  margin: 24px 16px 0;
}

.brand-btn {
  background-color: var(--primary, #f2a6b0);
  border-color: var(--primary, #f2a6b0);
  color: #ffffff;
  font-weight: 600;
  font-size: 16px;
  box-shadow: 0 4px 20px rgba(242, 166, 176, 0.35);
  transition: all 0.3s ease;
}

.brand-btn:active {
  background-color: var(--primary-hover, #e8919c);
  border-color: var(--primary-hover, #e8919c);
  transform: translateY(2px);
}

.reset-desc {
  font-size: 14px;
  color: var(--text-gray, #6b5f5a);
  margin-bottom: 16px;
  text-align: center;
  line-height: 1.5;
  padding: 0 10px;
}

.links {
  margin-top: auto;
  padding-top: 40px;
  text-align: center;
  font-size: 14px;
}

.links a {
  color: var(--primary, #f2a6b0);
  font-weight: 600;
  transition: color 0.2s;
}

.divider {
  color: var(--border-color, #f0e8e5);
  margin: 0 12px;
}
</style>