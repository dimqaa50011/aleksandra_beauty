
CORS_ALLOWED_ORIGINS = [
    "https://sasha-sugar.ru",
    "https://www.sasha-sugar.ru",
    "https://web.telegram.org",   # Для тестов в веб-версии Telegram
    "https://vk.com",
    "https://new.vk.com",   # Основной домен ВК в десктопной версии сейчас
    "https://m.vk.com",
]

CSRF_TRUSTED_ORIGINS = [
    "https://sasha-sugar.ru",
    "https://www.sasha-sugar.ru",
    "https://web.telegram.org",
    "https://vk.com",
    "https://new.vk.com",   # Основной домен ВК в десктопной версии сейчас
    "https://m.vk.com",
]

CORS_ALLOW_CREDENTIALS = True
