import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Vant, { Locale } from 'vant'
import ruRU from 'vant/es/locale/lang/ru-RU'
import 'vant/lib/index.css'
import './style.css'
import App from './App.vue'
import router from './router'
import { initPlatformSDK } from './utils/platform'

// Устанавливаем русский язык для всех компонентов Vant (кнопки, календари и т.д.)
Locale.use('ru-RU', ruRU)

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(Vant)

// Слушаем сообщения от Service Worker (для пушей)
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'NAVIGATE_TO') {
      const url = event.data.url
      const cleanUrl = url.replace('/cabinet', '')
      router.push(cleanUrl)
    }
  })
}

// Сразу монтируем приложение
app.mount('#app')

// А SDK грузим в фоне
initPlatformSDK().then(() => {
  console.log('Platform SDK ready')
}).catch((e) => {
  console.warn('Platform SDK error:', e)
})