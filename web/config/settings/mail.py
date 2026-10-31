
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.yandex.ru'       # Пример для Яндекс Почты
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'dz5011@yandex.ru'
EMAIL_HOST_PASSWORD = "vjoafohcczjunxdy"
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER  # Отправитель по умолчанию


# settings.py

MAILERS = {
    "default": {  # Конфигурация по умолчанию
        "BACKEND": EMAIL_BACKEND,
        "OPTIONS": {
            "host": "smtp.yandex.ru",
            "port": 587,
            "use_tls": True,
            "username": EMAIL_HOST_USER,
            "password": EMAIL_HOST_PASSWORD,
        },
    },
    # Здесь можно добавить другие конфигурации, например, для уведомлений
}

