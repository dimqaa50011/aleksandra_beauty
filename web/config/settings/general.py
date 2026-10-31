import os
from pathlib import Path
from environs import Env



# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = Env()
env.read_env(BASE_DIR / ".env.prod")


SECRET_KEY = env.str('SECRET_KEY')

# DEBUG должен быть булевым. В .env мы храним его как '0' или '1'
DEBUG = env.bool('DEBUG')


ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')


DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    
]

EXTENSIONS_APPS = [
    'corsheaders',
    'rest_framework',
    'rest_framework.authtoken',
    'django_q',
    
    
]

DEV_EXTENSIONS_APPS = [
    
]

PROJECTS_APP = [
    'booking_app',
    'beauty_app',
    'cert_app',
    'gen_posts_app',
    'stats_app',
    'cabinet_app',
]

if DEBUG:
    EXTENSIONS_APPS += DEV_EXTENSIONS_APPS


INSTALLED_APPS = DJANGO_APPS + EXTENSIONS_APPS + PROJECTS_APP




MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'booking_app.middleware.APITokenMiddleware',
]



ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [ BASE_DIR / 'templates',],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'booking_app.context_processors.pwa_settings',
                'beauty_app.context_processors.faq_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


if DEBUG:
    DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "db.sqlite3",
    }
}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env.str('POSTGRES_DB'),
            'USER': env.str('POSTGRES_USER'),
            'PASSWORD': env.str('POSTGRES_PASSWORD'),
            'HOST': env.str('POSTGRES_HOST', default='db'), # 'db' - это имя сервиса в docker-compose
            'PORT': env.str('POSTGRES_PORT', default='5432'),
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'ru'

# Часовой пояс (для Санкт-Петербурга)
TIME_ZONE = 'Europe/Moscow'

# Обязательно добавь эти настройки, если их нет:
USE_I18N = True  # Включает поддержку интернационализации
USE_L10N = True  # Включает локализацию форматов (даты, числа)
USE_TZ = True    # Включает поддержку часовых поясов

# Список поддерживаемых языков (опционально, но полезно)
LANGUAGES = [
    ('ru', 'Русский'),
]



# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
STATIC_URL = '/static/'
MEDIA_URL = '/media/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Куда команда collectstatic будет собирать все файлы для продакшена
# (Nginx будет раздавать файлы именно отсюда)
STATIC_ROOT = BASE_DIR / 'staticfiles'


MEDIA_ROOT = BASE_DIR / "media"


EMAIL_HOST_PASSWORD = env.str('EMAIL_HOST_PASSWORD')
CERT_SECRET = env.str('CERT_SECRET')
ADMIN_API_SECRET = env.str('ADMIN_API_SECRET')
WEB_PASSWORDS = env.list('WEB_PASSWORDS', subcast=str, default=[])

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/admin-dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# Сообщения
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.ERROR: 'error',
    messages.SUCCESS: 'success',
}


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'gigachat-cache',
    }
}



LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} [{module}:{lineno}] {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # django.request шумит на 404 — оставим только реальные проблемы
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'WARNING',   # в dev можно DEBUG — см. development.py
            'propagate': False,
        },
        'cabinet_app': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'booking_app': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'cert_app': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'beauty_app': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}


LOGGING['loggers']['django.server'] = {
    'handlers': ['console'],
    'level': 'WARNING',
    'propagate': False,
}