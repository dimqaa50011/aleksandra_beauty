import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Vant from 'vant'
import 'vant/lib/index.css'
import './style.css'
import App from './App.vue'
import router from './router'
import { initPlatformSDK } from './utils/platform'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(Vant)

// 1. Слушаем сообщения от Service Worker (для пушей)
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'NAVIGATE_TO') {
      const url = event.data.url
      const cleanUrl = url.replace('/cabinet', '')
      router.push(cleanUrl)
    }
  })
}

// 2. Сразу монтируем приложение (пользователь увидит интерфейс)
app.mount('#app')

// 3. А SDK грузим в фоне (если в ТГ - он сам обновит состояние)
initPlatformSDK().then(() => {
  console.log('Platform SDK ready');
})