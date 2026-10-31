<template>
  <van-tabbar v-model="active" route active-color="#f2a6b0" inactive-color="#9c928e" class="custom-tabbar">
    <van-tabbar-item replace to="/" icon="home-o">Главная</van-tabbar-item>
    <van-tabbar-item replace to="/appointments" icon="calendar-o">Визиты</van-tabbar-item>
    <van-tabbar-item replace to="/bonuses" icon="gift-o">Бонусы</van-tabbar-item>
    <van-tabbar-item replace to="/profile" icon="user-o">Профиль</van-tabbar-item>
  </van-tabbar>
</template>

<script setup lang="ts">
import { ref } from 'vue'
// Vant сам синхронизирует активный таб с текущим маршрутом благодаря prop "route"
const active = ref(0)
</script>

<style scoped>
.custom-tabbar {
  border-top: 1px solid #f0e8e5;
  padding-bottom: env(safe-area-inset-bottom); /* Для iPhone с "челкой" */
}
</style>