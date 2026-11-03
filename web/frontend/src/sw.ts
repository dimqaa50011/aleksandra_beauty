/// <reference lib="webworker" />
import { precacheAndRoute } from 'workbox-precaching'

declare let self: ServiceWorkerGlobalScope

precacheAndRoute(self.__WB_MANIFEST)

self.addEventListener('push', (event: PushEvent) => {
  if (event.data) {
    const data = event.data.json()
    const options = {
      body: data.body,
      icon: '/cabinet/icons/icon-192x192.png',
      badge: '/cabinet/icons/icon-192x192.png',
      data: { url: data.url || '/cabinet/' }, // Ссылка на /notifications/123
      vibrate: [200, 100, 200],
      requireInteraction: true
    }
    event.waitUntil(self.registration.showNotification(data.title, options))
  }
})

self.addEventListener('notificationclick', (event: NotificationEvent) => {
  event.notification.close()
  const urlToOpen = event.notification.data?.url || '/cabinet/'

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      // 1. Если приложение уже открыто — шлем сообщение для Vue Router
      for (const client of windowClients) {
        if (client.url.includes('/cabinet/') && 'focus' in client) {
          client.postMessage({
            type: 'NAVIGATE_TO',
            url: urlToOpen
          });
          return (client as WindowClient).focus();
        }
      }
      // 2. Если закрыто — открываем новое окно
      if (self.clients.openWindow) {
        return self.clients.openWindow(urlToOpen);
      }
    })
  )
})