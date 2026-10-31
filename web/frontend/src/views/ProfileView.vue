<template>
  <div class="profile-page">
    <div class="page-header">
      <h1>Профиль</h1>
    </div>

    <!-- АВАТАРКА И ИМЯ -->
    <div class="user-hero">
      <van-uploader :after-read="onAvatarUpload" accept="image/*" :max-size="5 * 1024 * 1024" @oversize="onOversize">
        <div class="avatar-wrapper">
          <img v-if="user?.avatar" :src="user.avatar" class="avatar-img" alt="Аватар" />
          <div v-else class="avatar">
            {{ user?.name ? user.name.charAt(0).toUpperCase() : 'S' }}
          </div>
          <div class="avatar-edit-badge">
            <van-icon name="photograph" size="14" color="#fff" />
          </div>
        </div>
      </van-uploader>
      
      <h2>{{ user?.name || 'Гость' }}</h2>
      <p>+{{ user?.phone }}</p>
    </div>

    <!-- БЛОК БОНУСОВ -->
    <div class="stats-grid">
      <div class="stat-box">
        <div class="stat-val">{{ user?.bonus_balance || 0 }}</div>
        <div class="stat-lbl">бонусов на счету</div>
      </div>
    </div>

    <!-- Любимая услуга -->
    <div class="favorite-service" v-if="user?.favorite_service">
      <van-icon name="like-o" color="#f2a6b0" size="20" />
      <span>Любимая услуга: <strong>{{ user.favorite_service.name }}</strong></span>
    </div>

    <!-- НАСТРОЙКИ ПРОФИЛЯ -->
    <div class="section-title">Личные данные</div>
    <van-cell-group inset class="custom-group">
      <van-field
        v-model="editName"
        label="Имя"
        placeholder="Ваше имя"
        :border="false"
      />
      <van-field
        v-model="editEmail"
        label="Email"
        placeholder="example@mail.ru"
        type="email"
        :border="false"
      />
    </van-cell-group>
    <div class="save-btn-wrap" v-if="isDataChanged">
      <van-button round block size="small" type="primary" class="brand-btn" @click="saveProfile" :loading="saving">
        Сохранить изменения
      </van-button>
    </div>

    <!-- НАСТРОЙКИ УВЕДОМЛЕНИЙ -->
    <div class="section-title">Уведомления</div>
    <van-cell-group inset class="custom-group">
      <van-cell center title="Согласие на маркетинг">
        <template #label>
          <span class="cell-label">Получать скидки и акции</span>
        </template>
        <template #right-icon>
          <van-switch 
            v-model="consentMarketing" 
            size="24px" 
            active-color="#f2a6b0" 
            @change="toggleMarketing"
          />
        </template>
      </van-cell>
      
      <van-cell center title="Push-уведомления">
        <template #label>
          <span class="cell-label">Напоминания о визитах</span>
        </template>
        <template #right-icon>
          <van-switch 
            v-model="pushEnabled" 
            size="24px" 
            active-color="#f2a6b0" 
            @click="togglePush"
          />
        </template>
      </van-cell>
    </van-cell-group>

    <!-- КНОПКА ВЫХОДА -->
    <div class="logout-wrap">
      <van-button plain round block type="danger" @click="handleLogout">
        Выйти из аккаунта
      </van-button>
    </div>

    <BottomTabbar />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showSuccessToast, showFailToast, showLoadingToast, closeToast } from 'vant'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'
import BottomTabbar from '@/components/BottomTabbar.vue'

const router = useRouter()
const authStore = useAuthStore()

const user = computed(() => authStore.user)

// Редактирование данных
const editName = ref('')
const editEmail = ref('')
const saving = ref(false)

const isDataChanged = computed(() => {
  return (editName.value !== (user.value?.name || '')) || 
         (editEmail.value !== (user.value?.email || ''))
})

// Настройки
const consentMarketing = ref(false)
const pushEnabled = ref(true)

// --- ЗАГРУЗКА АВАТАРКИ ---
async function onAvatarUpload(file: any) {
  const formData = new FormData()
  formData.append('avatar', file.file)

  showLoadingToast({ message: 'Загрузка...', forbidClick: true })

  try {
    const { data } = await apiClient.post('/me/avatar/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    
    if (authStore.user) {
      authStore.user.avatar = data.avatar
    }
    closeToast()
    showSuccessToast('Аватар обновлен')
  } catch (error: any) {
    closeToast()
    showFailToast(error.response?.data?.error || 'Ошибка загрузки')
  }
}

function onOversize() {
  showFailToast('Файл слишком большой (макс 5МБ)')
}

// --- СОХРАНЕНИЕ ПРОФИЛЯ ---
async function saveProfile() {
  saving.value = true
  try {
    await authStore.updateProfile({
      name: editName.value,
      email: editEmail.value
    })
    showSuccessToast('Данные сохранены')
  } catch (error) {
    showFailToast('Ошибка при сохранении')
  } finally {
    saving.value = false
  }
}

async function toggleMarketing(val: boolean) {
  try {
    await authStore.updateConsents({ consent_marketing: val })
    showSuccessToast(val ? 'Вы подписаны на рассылку' : 'Рассылка отключена')
  } catch (error) {
    consentMarketing.value = !val
    showFailToast('Не удалось изменить настройку')
  }
}

function togglePush() {
  showFailToast('Push-уведомления будут доступны в ближайшем обновлении')
  setTimeout(() => { pushEnabled.value = !pushEnabled.value }, 0)
}

async function handleLogout() {
  await authStore.logout()
  router.push({ name: 'login' })
}

onMounted(async () => {
  await authStore.fetchMe()
  
  editName.value = user.value?.name || ''
  editEmail.value = user.value?.email || ''
  consentMarketing.value = user.value?.consent_marketing || false
})
</script>

<style scoped>
.profile-page {
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

/* Профиль сверху */
.user-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 24px;
}

.avatar-wrapper {
  position: relative;
  display: inline-block;
  margin-bottom: 12px;
  cursor: pointer;
}

.avatar-img {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid var(--primary, #f2a6b0);
  box-shadow: 0 4px 15px rgba(242, 166, 176, 0.2);
}

.avatar {
  width: 80px;
  height: 80px;
  background-color: #fff;
  border: 2px solid var(--primary, #f2a6b0);
  color: var(--primary, #f2a6b0);
  font-weight: 700;
  font-size: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 15px rgba(242, 166, 176, 0.2);
}

.avatar-edit-badge {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 28px;
  height: 28px;
  background-color: var(--primary, #f2a6b0);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.user-hero h2 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-dark, #2d2a28);
  margin: 0 0 4px 0;
}

.user-hero p {
  font-size: 14px;
  color: var(--text-gray, #6b5f5a);
  margin: 0;
}

/* Статистика */
.stats-grid {
  display: flex;
  gap: 8px;
  padding: 0 16px;
  margin-bottom: 16px;
}

.stat-box {
  flex: 1;
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  text-align: center;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.02);
  border: 1px solid #f0e8e5;
}

.stat-val {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-dark, #2d2a28);
  margin-bottom: 4px;
}

.stat-lbl {
  font-size: 12px;
  color: var(--text-gray, #6b5f5a);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.favorite-service {
  margin: 0 16px 24px;
  background: #fff0f2;
  border-radius: 12px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: #d85c6b;
}

/* Секции */
.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-gray, #6b5f5a);
  margin: 0 0 8px 20px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Группы Vant */
.custom-group {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.02);
  border: 1px solid #f0e8e5;
  margin-bottom: 24px;
  overflow: hidden;
}

:deep(.van-field__label) {
  color: var(--text-gray, #6b5f5a);
  font-size: 14px;
  width: 60px;
}

:deep(.van-field__control) {
  color: var(--text-dark, #2d2a28);
  font-size: 15px;
}

:deep(.van-cell__title) {
  font-size: 15px;
  color: var(--text-dark, #2d2a28);
}

.cell-label {
  font-size: 12px;
  color: var(--text-gray, #6b5f5a);
  margin-top: 2px;
  display: block;
}

.save-btn-wrap {
  padding: 0 16px;
  margin-top: -12px;
  margin-bottom: 24px;
}

.brand-btn {
  background-color: var(--primary, #f2a6b0);
  border-color: var(--primary, #f2a6b0);
}

/* Выход */
.logout-wrap {
  padding: 0 16px;
  margin-top: 32px;
  margin-bottom: 24px;
}
</style>