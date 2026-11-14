from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from cabinet_app.models import CabinetUser

from .base import CabinetAPIView
from ..serializers.profile import ClientProfileSerializer
from rest_framework.response import Response
from rest_framework import status
from booking_app.models import Client
from booking_app.utils import find_client_by_phone, normalize_phone

class BindPhoneView(CabinetAPIView):
    """PATCH: Привязка телефона к аккаунту (для новых юзеров из соцсетей)."""

    def patch(self, request):
        user = request.user
        raw_phone = request.data.get('phone', '')
        normalized = normalize_phone(raw_phone)

        if not normalized:
            return Response({'error': 'Неверный формат телефона'}, status=400)

        # Проверяем, не занят ли этот телефон другим CabinetUser
        if CabinetUser.objects.filter(phone=normalized).exclude(pk=user.pk).exists():
            return Response({'error': 'Этот телефон уже привязан к другому аккаунту'}, status=400)

        # Ищем существующего Client в CRM
        client = find_client_by_phone(raw_phone)
        if not client:
            # Если в CRM нет, создаем нового
            client = Client.objects.create(phone=raw_phone, name=user.name)
        
        # Привязываем Client к CabinetUser и обновляем телефон
        user.client = client
        user.phone = normalized
        user.save()

        return Response({'success': True, 'message': 'Телефон привязан'})


class MeView(CabinetAPIView):
    """GET: Профиль и статистика. PATCH: Обновление имени и email."""

    def get(self, request):
        client = request.user.client
        serializer = ClientProfileSerializer(client)
        return Response(serializer.data)

    def patch(self, request):
        client = request.user.client
        serializer = ClientProfileSerializer(client, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UpdateConsentsView(CabinetAPIView):
    """PATCH: Обновление согласий (маркетинг, пуши)."""

    def patch(self, request):
        user = request.user
        marketing = request.data.get('consent_marketing')
        
        if marketing is not None:
            user.consent_marketing = bool(marketing)
            user.consent_marketing_at = timezone.now() if marketing else None
            user.save(update_fields=['consent_marketing', 'consent_marketing_at'])
            
        return Response({
            'success': True,
            'consent_marketing': user.consent_marketing
        })


class AvatarUploadView(CabinetAPIView):
    """POST: Загрузка аватара клиента."""
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        file = request.FILES.get('avatar')
        if not file:
            return Response({'error': 'Файл не передан'}, status=status.HTTP_400_BAD_REQUEST)
        
        if file.size > 5 * 1024 * 1024:
            return Response({'error': 'Файл слишком большой (макс 5МБ)'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user.avatar = file
        user.save()

        avatar_url = request.build_absolute_uri(user.avatar.url) if user.avatar else None
        return Response({'avatar': avatar_url})