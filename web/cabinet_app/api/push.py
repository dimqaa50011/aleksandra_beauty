from django.conf import settings
from rest_framework.response import Response
from rest_framework import status

from .base import CabinetAPIView
from ..models import ClientPushSubscription


class PushVapidKeyView(CabinetAPIView):
    """GET: Отдает публичный ключ VAPID для подписки фронтенда."""
    def get(self, request):
        return Response({
            'publicKey': settings.VAPID_PUBLIC_KEY
        })


class PushSubscribeView(CabinetAPIView):
    """POST: Сохраняет подписку устройства на пуши."""
    def post(self, request):
        data = request.data
        endpoint = data.get('endpoint')
        keys = data.get('keys', {})
        
        if not endpoint or not keys.get('p256dh') or not keys.get('auth'):
            return Response(
                {'error': 'Неверные данные подписки'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Обновляем или создаем подписку для текущего пользователя
        ClientPushSubscription.objects.update_or_create(
            user=request.user,
            endpoint=endpoint,
            defaults={
                'p256dh': keys['p256dh'],
                'auth': keys['auth'],
                'platform': data.get('platform', ''),
                'is_standalone': data.get('is_standalone', False),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:255],
                'is_active': True
            }
        )
        return Response({'success': True})