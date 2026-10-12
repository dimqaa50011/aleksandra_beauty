from django.http import JsonResponse
from .models import APIToken
from django.utils import timezone

class APITokenMiddleware:
    """Проверяет API токен в заголовке запроса"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Проверяем только API endpoints
        if request.path.startswith('/api/') and request.method in ['POST', 'PUT', 'DELETE']:
            token = request.META.get('HTTP_X_API_TOKEN') or request.GET.get('token')
            
            if not token:
                return JsonResponse({'error': 'Отсутствует API токен'}, status=401)
            
            try:
                api_token = APIToken.objects.get(token=token, is_active=True)
                api_token.last_used = timezone.now()
                api_token.save(update_fields=['last_used'])
                request.api_token = api_token
            except APIToken.DoesNotExist:
                return JsonResponse({'error': 'Недействительный API токен'}, status=403)
        
        response = self.get_response(request)
        return response