const CACHE_NAME = 'sasha-sugar-v1';

// ============================================
// 1. Установка и кэширование
// ============================================
self.addEventListener('install', event => {
    console.log('[SW] Установлен');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[SW] Кэшируем главную');
                return cache.addAll(['/']);
            })
            .then(() => self.skipWaiting()) // Активируем сразу, не ждём закрытия вкладок
    );
});

// ============================================
// 2. Активация и очистка старых кэшей
// ============================================
self.addEventListener('activate', event => {
    console.log('[SW] Активирован');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(name => name !== CACHE_NAME)
                    .map(name => {
                        console.log('[SW] Удаляем старый кэш:', name);
                        return caches.delete(name);
                    })
            );
        }).then(() => self.clients.claim()) // Берём контроль над всеми вкладками сразу
    );
});

// ============================================
// 3. Обработка push-уведомлений
// ============================================
self.addEventListener('push', event => {
    console.log('[SW] Получен push:', event);
    
    let data = {};
    try {
        data = event.data ? event.data.json() : {};
    } catch (e) {
        console.error('[SW] Ошибка парсинга push-данных:', e);
        data = { title: 'Sasha Sugar', body: 'Новое уведомление' };
    }
    
    const options = {
        body: data.body || 'Новое уведомление',
        icon: '/static/images/favico.png',  // <-- Проверь, что файл существует!
        badge: '/static/images/favico.png',
        vibrate: [100, 50, 100],
        data: { url: data.url || '/' },
        tag: 'sasha-sugar-notification', // Чтобы не дублировать уведомления
        requireInteraction: false
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title || 'Sasha Sugar', options)
    );
});

// ============================================
// 4. Клик по уведомлению
// ============================================
self.addEventListener('notificationclick', event => {
    console.log('[SW] Клик по уведомлению');
    event.notification.close();
    
    const urlToOpen = event.notification.data.url || '/';
    
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then(clientList => {
                // Ищем уже открытую вкладку с нужным URL
                for (const client of clientList) {
                    if (client.url === urlToOpen && 'focus' in client) {
                        return client.focus();
                    }
                }
                // Если такой вкладки нет — открываем новую
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});

// ============================================
// 5. Обработка закрытия уведомления
// ============================================
self.addEventListener('notificationclose', event => {
    console.log('[SW] Уведомление закрыто пользователем');
});