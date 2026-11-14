import bridge from '@vkontakte/vk-bridge'

export type PlatformType = 'pwa' | 'telegram' | 'vk' | 'max'

export const getPlatform = (): PlatformType => {
  if (window.Telegram?.WebApp?.initData) return 'telegram'
  if (window.WebApp?.initData) return 'max'
  if (window.vkBridge) return 'vk'
  return 'pwa'
}

// Инициализация при старте
export const initPlatform = async () => {
  const platform = getPlatform()

  if (platform === 'telegram') {
    window.Telegram.WebApp.ready()
    window.Telegram.WebApp.expand() // На весь экран
  } 
  else if (platform === 'max') {
    // Обычно в MAX не нужна явная инициализация, но проверь доки
  } 
  else if (platform === 'vk') {
    await bridge.send('VKWebAppInit')
  }

  return platform
}