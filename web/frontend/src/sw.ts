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
  event.notification.close();
  
  // Берем URL из данных уведомления или ведем на общий список
  const urlToOpen = event.notification.data?.url || '/cabinet/notifications';

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      // 1. Ищем уже открытое окно нашего приложения
      for (const client of windowClients) {
        if (client.url.includes('/cabinet/') && 'focus' in client) {
          // 2. Если нашли — фокусируемся и ПРИНУДИТЕЛЬНО переходим по URL
          return (client as WindowClient).focus().then(() => {
            return (client as WindowClient).navigate(urlToOpen);
          });
        }
      }
      
      // 3. Если приложение закрыто — открываем новое окно с нужным URL
      if (self.clients.openWindow) {
        return self.clients.openWindow(urlToOpen);
      }
    })
  );
});