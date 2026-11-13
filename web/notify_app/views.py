from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import BroadcastMessage, NotificationType
from .serializers import NotificationTypeSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django_q.tasks import async_task
from .models import NotificationType



class AdminBroadcastAPIView(APIView):
    """POST: Запустить массовую рассылку."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        type_code = request.data.get('type_code', 'marketing')
        title = request.data.get('title')
        body = request.data.get('body')
        methods = request.data.get('methods', ['push']) # ['push', 'sms']
        send_to_all = request.data.get('send_to_all', True)
        client_ids = request.data.get('client_ids', None) # список ID, если не всем
        action_url = request.data.get('action_url', '/cabinet/')

        if not title or not body or not methods:
            return Response({'error': 'Заполните все поля и выберите хотя бы один способ'}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем, что тип существует
        if not NotificationType.objects.filter(code=type_code, is_active=True).exists():
            return Response({'error': 'Тип уведомления не найден'}, status=status.HTTP_404_NOT_FOUND)

        # Сохраняем историю
        BroadcastMessage.objects.create(
            title=title,
            body=body,
            methods=methods,
            recipients_type='all' if send_to_all else 'specific',
            recipients_count=0 if send_to_all else len(client_ids or []),
            created_by=request.user
        )

        # Запускаем в фоне
        async_task(
            'notify_app.tasks.task_send_broadcast',
            title, body, methods, type_code, action_url,
            None if send_to_all else client_ids
        )

        return Response({'success': True, 'message': 'Рассылка запущена в фоне'})

class AdminNotificationTypeListCreateView(generics.ListCreateAPIView):
    """GET: Список всех типов. POST: Создать новый тип."""
    queryset = NotificationType.objects.all().order_by('category', 'name')
    serializer_class = NotificationTypeSerializer
    permission_classes = [IsAuthenticated]

class AdminNotificationTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET: Один тип. PUT/PATCH: Обновить. DELETE: Удалить."""
    queryset = NotificationType.objects.all()
    serializer_class = NotificationTypeSerializer
    permission_classes = [IsAuthenticated]