<template>
  <van-tabbar v-model="active" route active-color="#f2a6b0" inactive-color="#9c928e" class="custom-tabbar">
    <van-tabbar-item replace to="/" icon="home-o">Главная</van-tabbar-item>
    <van-tabbar-item replace to="/appointments" icon="calendar-o">Визиты</van-tabbar-item>
    
    <!-- НОВАЯ ВКЛАДКА -->
    <van-tabbar-item replace to="/notifications" icon="bell">
      <template #icon>
        <van-badge :content="notifStore.unreadCount > 0 ? notifStore.unreadCount : ''" max="9">
          <van-icon name="bell" size="22" />
        </van-badge>
      </template>
      Уведомления
    </van-tabbar-item>

    <van-tabbar-item replace to="/bonuses" icon="gift-o">Бонусы</van-tabbar-item>
    <van-tabbar-item replace to="/profile" icon="user-o">Профиль</van-tabbar-item>
  </van-tabbar>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useNotificationStore } from '@/stores/notifications'

const active = ref(0)
const notifStore = useNotificationStore()

onMounted(() => {
  notifStore.fetchUnreadCount()
})
</script>

<style scoped>
.custom-tabbar {
  border-top: 1px solid #f0e8e5;
  padding-bottom: env(safe-area-inset-bottom);
}
/* Уменьшаем шрифт, чтобы 5 вкладок влезли */
:deep(.van-tabbar-item__text) {
  font-size: 10px;
}
</style>