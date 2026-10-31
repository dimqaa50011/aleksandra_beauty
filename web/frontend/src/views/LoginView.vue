<template>
  <div class="login-page">
    <div class="header">
      <div class="logo-circle">S</div>
      <h1>С возвращением!</h1>
      <p>Войдите в личный кабинет</p>
    </div>

    <van-form @submit="onSubmit" class="form-container">
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
          round 
          block 
          type="primary" 
          native-type="submit" 
          :loading="loading"
          loading-text="Входим..."
          class="brand-btn"
        >
          Войти
        </van-button>
      </div>
    </van-form>

    <div class="links">
      <router-link to="/register">У меня нет аккаунта</router-link>
      <span class="divider">•</span>
      <a href="#" @click.prevent="showResetTip">Забыли пароль?</a>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { showFailToast, showSuccessToast, showDialog } from 'vant'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const phone = ref('')
const password = ref('')
const loading = ref(false)

async function onSubmit() {
  loading.value = true
  try {
    await authStore.login(phone.value, password.value)
    showSuccessToast('Успешный вход')
    router.push({ name: 'home' })
  } catch (error: any) {
    const msg = error.response?.data?.detail 
             || error.response?.data?.phone?.[0] 
             || error.response?.data?.password?.[0]
             || 'Неверный телефон или пароль'
    showFailToast(msg)
  } finally {
    loading.value = false
  }
}

function showResetTip() {
  showDialog({
    title: 'Сброс пароля',
    message: 'Функция сброса пароля появится в ближайшее время. Пока обратитесь к администратору.',
  })
}
</script>

<style scoped>
/* Используем переменные с сайта */
.login-page {
  min-height: 100vh;
  padding: 40px 20px;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-light, #fef9f7); /* Светлый фон сайта */
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
  /* Тень как у кнопок на сайте */
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

/* Стилизация группы полей Vant */
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

/* Кнопка в стиле сайта */
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
  box-shadow: 0 2px 10px rgba(242, 166, 176, 0.2);
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

.links a:hover {
  color: var(--primary-hover, #e8919c);
}

.divider {
  color: var(--border-color, #f0e8e5);
  margin: 0 12px;
}
</style>