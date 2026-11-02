import apiClient from '@/api/client'

// Конвертация ключа из base64
function urlBase64ToUint8Array(base64String: string) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)))
}

export async function subscribeToPush() {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    throw new Error('Push API не поддерживается вашим браузером')
  }

  // 1. Запрашиваем разрешение
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') {
    throw new Error('Вы отклонили запрос на уведомления')
  }

  // 2. Получаем регистрацию Service Worker
  const registration = await navigator.serviceWorker.ready

  // 3. Получаем публичный VAPID ключ с бэкенда
  const { data } = await apiClient.get('/push/vapid-key/')
  
  // 4. Подписываемся
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(data.publicKey)
  })

  // 5. Отправляем на бэкенд
  const subJson = subscription.toJSON()
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches

  await apiClient.post('/push/subscribe/', {
    endpoint: subJson.endpoint,
    keys: subJson.keys,
    platform: navigator.platform,
    is_standalone: isStandalone
  })
  
  return subscription
}