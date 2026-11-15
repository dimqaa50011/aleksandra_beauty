from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from .base import CabinetAPIView
from ..serializers.profile import ClientProfileSerializer
from booking_app.models import Client
from booking_app.utils import find_client_by_phone, normalize_phone
from ..models import CabinetUser, ClientRefreshToken
from ..authentication import issue_access_token
from .auth import _set_refresh_cookie, _user_payload


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
        
        if file.size > 5 * 1024 * 1024: # Лимит 5 МБ
            return Response({'error': 'Файл слишком большой (макс 5МБ)'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user.avatar = file
        user.save()

        avatar_url = request.build_absolute_uri(user.avatar.url) if user.avatar else None
        return Response({'avatar': avatar_url})


class BindPhoneView(CabinetAPIView):
    """PATCH: Привязка реального телефона к аккаунту (слияние аккаунтов)."""

    def patch(self, request):
        current_user = request.user
        raw_phone = request.data.get('phone', '')
        normalized = normalize_phone(raw_phone)

        if not normalized:
            return Response({'error': 'Неверный формат телефона'}, status=400)

        # 1. Ищем, есть ли УЖЕ аккаунт в PWA с таким телефоном
        existing_user = CabinetUser.objects.filter(phone=normalized).exclude(pk=current_user.pk).first()

        if existing_user:
            # СЛИЯНИЕ АККАУНТОВ (Merge)
            # Переносим ID соцсети от временного пользователя к существующему
            if current_user.vk_id and not existing_user.vk_id:
                existing_user.vk_id = current_user.vk_id
            if current_user.telegram_id and not existing_user.telegram_id:
                existing_user.telegram_id = current_user.telegram_id
            if current_user.max_id and not existing_user.max_id:
                existing_user.max_id = current_user.max_id
            
            existing_user.save()

            # Запоминаем временного клиента и удаляем временного пользователя
            temp_client = current_user.client
            current_user.delete()
            
            # Удаляем временный Client, если он был создан для соцсети (vk_123, telegram_123 и т.д.)
            if temp_client and (
                temp_client.phone.startswith('vk_') or 
                temp_client.phone.startswith('telegram_') or 
                temp_client.phone.startswith('max_')
            ):
                temp_client.delete()

            # Выдаем НОВЫЕ токены для входа в СТАРЫЙ аккаунт
            access = issue_access_token(existing_user)
            _, refresh_raw = ClientRefreshToken.issue(existing_user, platform='merge')
            
            resp = Response({
                'success': True, 
                'access': access,
                'user': _user_payload(existing_user)
            })
            _set_refresh_cookie(resp, refresh_raw)
            return resp

        # 2. Если конфликта нет (телефон новый) - просто обновляем временный аккаунт
        real_client = find_client_by_phone(raw_phone)
        
        if not real_client:
            current_user.client.phone = normalized
            current_user.client.save()
        else:
            temp_client = current_user.client
            current_user.client = real_client
            current_user.save()
            if temp_client.pk != real_client.pk:
                temp_client.delete()

        current_user.phone = normalized
        current_user.save()

        return Response({'success': True, 'message': 'Телефон привязан'})