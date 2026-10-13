from django.conf import settings


def pwa_settings(request):
    """Добавляет VAPID ключ во все шаблоны для PWA-пушей"""
    return {
        'VAPID_PUBLIC_KEY': getattr(settings, 'VAPID_PUBLIC_KEY', ''),
    }