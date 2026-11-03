/// <reference lib="webworker" />
import { precacheAndRoute } from 'workbox-precaching'

declare let self: ServiceWorkerGlobalScope

// Кэширование (стандартное для Vite PWA)
precacheAndRoute(self.__WB_MANIFEST)

// Слушаем входящие пуши
self.addEventListener('push', (event: PushEvent) => {
  if (event.data) {
    try {
      const data = event.data.json()
      const options = {
        body: data.body,
        icon: '/cabinet/icons/icon-192x192.png',
        badge: '/cabinet/icons/icon-192x192.png',
        data: { url: data.url || '/cabinet/' },
        vibrate: [200, 100, 200],
        requireInteraction: true, // <--- ДОБАВИТЬ (не скрывать баннер сам)
        tag: 'sasha-sugar-notification' // Группировка
      }
      
      event.waitUntil(
        self.registration.showNotification(data.title, options)
      )
    } catch (e) {
      console.error('Ошибка парсинга пуша:', e)
    }
  }
})

// Обработка клика по уведомлению
self.addEventListener('notificationclick', (event: NotificationEvent) => {
  event.notification.close()
  const urlToOpen = event.notification.data?.url || '/cabinet/'

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      // Если приложение уже открыто — фокусируемся на нем
      for (const client of windowClients) {
        if (client.url.includes('/cabinet/') && 'focus' in client) {
          return (client as WindowClient).focus()
        }
      }
      // Иначе открываем новую вкладку
      if (self.clients.openWindow) {
        return self.clients.openWindow(urlToOpen)
      }
    })
  )
})