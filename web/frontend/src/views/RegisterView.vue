<template>
  <div class="register-page">
    <div class="header">
      <div class="logo-circle">S</div>
      <h1>Создать аккаунт</h1>
      <p>Присоединяйтесь к нашей студии</p>
    </div>

    <!-- Если есть реф-код, показываем приятную плашку -->
    <div v-if="referralCode" class="referral-banner">
      <van-icon name="gift-o" size="20" />
      <span>Вас пригласил друг! Вы получите бонусы после первого визита.</span>
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
          v-model="name"
          name="name"
          label="Имя"
          placeholder="Как к вам обращаться?"
          class="custom-field"
        />
        <van-field
          v-model="email"
          name="email"
          label="Email"
          placeholder="Для чеков (необязательно)"
          type="email"
          class="custom-field"
        />
        <van-field
          v-model="password"
          type="password"
          name="password"
          label="Пароль"
          placeholder="Минимум 8 символов"
          :rules="[{ required: true, message: 'Введите пароль' }, { validator: (val) => val.length >= 8, message: 'Минимум 8 символов' }]"
          class="custom-field"
        />
        <van-field
          v-model="passwordConfirm"
          type="password"
          name="password_confirm"
          label="Повтор"
          placeholder="Повторите пароль"
          :rules="[{ required: true, message: 'Повторите пароль' }, { validator: validateConfirm, message: 'Пароли не совпадают' }]"
          class="custom-field"
        />
      </van-cell-group>

      <!-- Согласия -->
      <div class="consents">
        <van-checkbox v-model="consentPd" shape="square" icon-size="18px" class="checkbox-item">
          <span class="consent-text">
            Я согласен на обработку <a href="#" @click.prevent="showPd">персональных данных</a>
          </span>
        </van-checkbox>
        
        <van-checkbox v-model="consentMarketing" shape="square" icon-size="18px" class="checkbox-item">
          <span class="consent-text">Хочу получать скидки и акции</span>
        </van-checkbox>
      </div>

      <div class="submit-btn">
        <van-button 
          round 
          block 
          type="primary" 
          native-type="submit" 
          :loading="loading"
          loading-text="Создаем..."
          :disabled="!consentPd"
          class="brand-btn"
        >
          Зарегистрироваться
        </van-button>
      </div>
    </van-form>

    <div class="links">
      <router-link to="/login">Уже есть аккаунт? Войти</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showFailToast, showSuccessToast, showDialog } from 'vant'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const phone = ref('')
const name = ref('')
const email = ref('')
const password = ref('')
const passwordConfirm = ref('')
const consentPd = ref(false)
const consentMarketing = ref(false)
const loading = ref(false)

// Забираем реф-код из URL (?ref=XXXX)
const referralCode = ref(route.query.ref as string || '')

// Валидация совпадения паролей для Vant
const validateConfirm = (val: string) => val === password.value

async function onSubmit() {
  if (!consentPd.value) {
    showFailToast('Необходимо согласие на обработку данных')
    return
  }

  loading.value = true
  try {
    await authStore.register({
      phone: phone.value,
      password: password.value,
      password_confirm: passwordConfirm.value,
      name: name.value,
      email: email.value,
      consent_pd: consentPd.value,
      consent_marketing: consentMarketing.value,
      ref: referralCode.value
    })
    showSuccessToast('Добро пожаловать!')
    router.push({ name: 'home' })
  } catch (error: any) {
    let msg = 'Ошибка регистрации. Проверьте данные.'
    if (error.response?.data) {
      const data = error.response.data
      // Достаем первую ошибку из ответа Django (например, phone или password)
      const firstError = Object.values(data)[0]
      if (Array.isArray(firstError)) msg = firstError[0]
      else if (typeof firstError === 'string') msg = firstError
    }
    showFailToast(msg)
  } finally {
    loading.value = false
  }
}

function showPd() {
  showDialog({
    title: 'Обработка данных',
    message: 'Текст политики конфиденциальности...',
  })
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  padding: 40px 20px;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-light, #fef9f7);
  font-family: 'Inter', sans-serif;
}

.header {
  text-align: center;
  margin-bottom: 24px;
  margin-top: 10px;
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

/* Плашка рефералки */
.referral-banner {
  background: #fff0f2;
  color: #d85c6b;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
  border: 1px solid #f9d1d6;
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
  padding: 14px 16px;
}

:deep(.van-field__label) {
  color: var(--text-gray, #6b5f5a);
  font-size: 14px;
  width: 70px;
}

:deep(.van-field__control) {
  color: var(--text-dark, #2d2a28);
  font-size: 15px;
}

/* Чекбоксы */
.consents {
  margin: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.checkbox-item {
  align-items: flex-start;
}

:deep(.van-checkbox__label) {
  margin-top: -2px; /* Выравнивание текста с иконкой */
}

.consent-text {
  font-size: 13px;
  color: var(--text-gray, #6b5f5a);
  line-height: 1.4;
}

.consent-text a {
  color: var(--primary, #f2a6b0);
  text-decoration: underline;
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

.brand-btn:active:not(:disabled) {
  background-color: var(--primary-hover, #e8919c);
  border-color: var(--primary-hover, #e8919c);
  transform: translateY(2px);
  box-shadow: 0 2px 10px rgba(242, 166, 176, 0.2);
}

.brand-btn:disabled {
  opacity: 0.6;
  background-color: var(--primary, #f2a6b0);
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
}
</style>