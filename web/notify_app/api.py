from rest_framework.response import Response
from rest_framework import status

# Импортируем базовый класс из кабинета, чтобы использовать JWT-аутентификацию
from cabinet_app.api.base import CabinetAPIView
from .models import NotificationType, ClientNotificationSetting


class NotificationSettingsView(CabinetAPIView):
    """GET: Получить настройки. PATCH: Обновить настройку."""

    def get(self, request):
        client = request.user.client
        types = NotificationType.objects.filter(is_active=True).order_by('category', 'id')
        
        result = []
        for t in types:
            # Ищем индивидуальную настройку клиента
            setting = ClientNotificationSetting.objects.filter(
                client=client, notification_type=t
            ).first()
            
            # Если настройки нет, берем дефолтную из типа
            is_enabled = setting.is_enabled if setting else t.default_enabled
            
            result.append({
                'code': t.code,
                'name': t.name,
                'description': t.description,
                'category': t.category,
                'is_enabled': is_enabled
            })
            
        return Response({'settings': result})

    def patch(self, request):
        client = request.user.client
        code = request.data.get('code')
        is_enabled = request.data.get('is_enabled')

        if code is None or is_enabled is None:
            return Response({'error': 'Не переданы code или is_enabled'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            n_type = NotificationType.objects.get(code=code, is_active=True)
        except NotificationType.DoesNotExist:
            return Response({'error': 'Тип уведомления не найден'}, status=status.HTTP_404_NOT_FOUND)

        # Обновляем или создаем настройку
        setting, created = ClientNotificationSetting.objects.update_or_create(
            client=client,
            notification_type=n_type,
            defaults={'is_enabled': is_enabled}
        )

        return Response({'success': True, 'is_enabled': setting.is_enabled})