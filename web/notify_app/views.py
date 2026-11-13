from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import NotificationType
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
        type_code = request.data.get('type_code')
        title = request.data.get('title')
        body = request.data.get('body')
        action_url = request.data.get('action_url', '/cabinet/')

        if not type_code or not title or not body:
            return Response({'error': 'Заполните все поля'}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем, существует ли такой тип и разрешает ли он пуши
        try:
            n_type = NotificationType.objects.get(code=type_code, is_active=True)
            if not n_type.allow_push:
                return Response({'error': 'Этот тип уведомлений не поддерживает Push'}, status=status.HTTP_400_BAD_REQUEST)
        except NotificationType.DoesNotExist:
            return Response({'error': 'Тип рассылки не найден'}, status=status.HTTP_404_NOT_FOUND)

        # Запускаем в фоне
        async_task(
            'notify_app.tasks.task_send_broadcast',
            type_code, title, body, action_url
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