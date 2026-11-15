export type Platform = 'pwa' | 'telegram' | 'vk' | 'max';

export function detectPlatform(): Platform {
  if (typeof window === 'undefined') return 'pwa';
  if (window.Telegram?.WebApp?.initData) return 'telegram';
  if (window.WebApp?.initData) return 'max';
  if (window.vkBridge) return 'vk';
  return 'pwa';
}

// Улучшенная загрузка скрипта с таймаутом
function loadScript(src: string, timeoutMs = 4000): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve();
      return;
    }

    const script = document.createElement('script');
    script.src = src;
    script.async = true;

    // Таймаут: если скрипт не загрузился (например, блокировка РКН), идем дальше
    const timeout = setTimeout(() => {
      script.remove(); // Убираем недогруженный скрипт
      reject(new Error(`Timeout loading script: ${src}`));
    }, timeoutMs);

    script.onload = () => {
      clearTimeout(timeout);
      resolve();
    };
    
    script.onerror = () => {
      clearTimeout(timeout);
      reject(new Error(`Failed to load script: ${src}`));
    };

    document.head.appendChild(script);
  });
}

export async function initPlatformSDK(): Promise<Platform> {
  const platform = detectPlatform();

  // Если мы не в соцсети, ничего не грузим
  if (platform === 'pwa') return platform;

  try {
    if (platform === 'telegram') {
      // Грузим с таймаутом, чтобы не вешать приложение
      await loadScript('https://telegram.org/js/telegram-web-app.js');
      // Если загрузилось - инициализируем
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
      }
    } 
    else if (platform === 'max') {
      await loadScript('https://st.max.ru/js/max-web-app.js');
    } 
    else if (platform === 'vk') {
      // Для VK используем npm-пакет
      const bridge = (await import('@vkontakte/vk-bridge')).default;
      await bridge.send('VKWebAppInit');
    }
  } catch (error) {
    // Если скрипт не загрузился (таймаут или ошибка), логируем и идем дальше.
    // Приложение уже смонтировано и покажет форму логина.
    console.warn(`Platform SDK init failed for ${platform}:`, error);
  }

  return platform;
}