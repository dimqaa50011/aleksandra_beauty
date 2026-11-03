from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .base import CabinetAPIView
from ..models import NotificationLog

class NotificationListView(CabinetAPIView):
    """GET: Список уведомлений клиента."""
    def get(self, request):
        notifications = NotificationLog.objects.filter(
            client=request.user.client,
            channel=NotificationLog.CHANNEL_PUSH # Показываем только пуши
        ).order_by('-created_at')

        data = []
        for notif in notifications:
            data.append({
                'id': notif.id,
                'title': notif.payload.get('title', 'Уведомление'),
                'body': notif.payload.get('body', ''),
                'url': notif.payload.get('url', ''),
                'is_read': notif.is_read,
                'created_at': notif.created_at.strftime('%d.%m.%Y %H:%M'),
            })
        return Response({'notifications': data})

class NotificationDetailView(CabinetAPIView):
    """GET: Детали одного уведомления + PATCH: Отметить прочитанным."""
    def get(self, request, pk):
        notif = get_object_or_404(NotificationLog, pk=pk, client=request.user.client)
        
        # Если открыли уведомление — считаем его прочитанным
        if not notif.is_read:
            notif.is_read = True
            notif.save(update_fields=['is_read'])

        return Response({
            'id': notif.id,
            'title': notif.payload.get('title', 'Уведомление'),
            'body': notif.payload.get('body', ''),
            'url': notif.payload.get('url', ''),
            'created_at': notif.created_at.strftime('%d.%m.%Y %H:%M'),
        })

class UnreadCountView(CabinetAPIView):
    """GET: Количество непрочитанных уведомлений (для бейджа)."""
    def get(self, request):
        count = NotificationLog.objects.filter(
            client=request.user.client,
            channel=NotificationLog.CHANNEL_PUSH,
            is_read=False
        ).count()
        return Response({'count': count})