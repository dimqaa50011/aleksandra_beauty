# booking_app/middleware.py
from django.http import JsonResponse
from .models import APIToken

class APITokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # СПИСОК ИСКЛЮЧЕНИЙ: пути, которые НЕ должны проверяться на API токен.
        # Мы добавили сюда '/api/save-push-subscription/', чтобы пуши работали из браузера.
        allowed_paths = [
            '/admin/',
            '/login/',
            '/logout/',
            '/api/save-push-subscription/', 
        ]
        
        # Если URL начинается с одного из разрешенных путей, пропускаем проверку токена
        if any(request.path.startswith(path) for path in allowed_paths):
            return self.get_response(request)

        # Проверяем наличие заголовка X-API-Token для остальных запросов
        token = request.headers.get('X-API-Token')
        if not token:
            return JsonResponse({'error': 'Отсутствует API токен'}, status=401)

        # Проверяем, есть ли такой активный токен в базе
        if not APIToken.objects.filter(token=token, is_active=True).exists():
            return JsonResponse({'error': 'Неверный или неактивный API токен'}, status=401)

        return self.get_response(request)