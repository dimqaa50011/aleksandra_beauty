from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from notify_app.notifiers import ClientNotify
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
        methods = request.data.get('methods', ['push']) 
        send_to_all = request.data.get('send_to_all', True)
        client_ids = request.data.get('client_ids', None) 
        action_url = request.data.get('action_url', '/cabinet/')

        if not title or not body or not methods:
            return Response({'error': 'Заполните все поля и выберите хотя бы один способ'}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем тип (на всякий случай)
        NotificationType.objects.get_or_create(
            code=type_code, 
            defaults={'name': 'Маркетинг', 'category': 'Маркетинг', 'allow_push': True, 'allow_sms': True}
        )

        # ВЫЗЫВАЕМ КЛАСС, А НЕ ФУНКЦИЮ НАПРЯМУЮ
        ClientNotify.broadcast(
            title=title,
            body=body,
            methods=methods,
            type_code=type_code,
            action_url=action_url,
            client_ids=None if send_to_all else client_ids
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