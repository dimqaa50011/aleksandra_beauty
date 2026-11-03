import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Vant from 'vant'
import 'vant/lib/index.css'
import './style.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(Vant)

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'NAVIGATE_TO') {
      const url = event.data.url
      // Убираем /cabinet, так как Vue Router сам его добавит
      const cleanUrl = url.replace('/cabinet', '')
      router.push(cleanUrl)
    }
  })
}


app.mount('#app')