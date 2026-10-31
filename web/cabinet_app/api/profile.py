from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from .base import CabinetAPIView
from ..serializers.profile import ClientProfileSerializer


class MeView(CabinetAPIView):
    """GET: Профиль и статистика. PATCH: Обновление имени и email."""

    def get(self, request):
        client = request.user.client
        serializer = ClientProfileSerializer(client)
        return Response(serializer.data)

    def patch(self, request):
        client = request.user.client
        # Разрешаем менять только name и email
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
            from django.utils import timezone
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

        # Возвращаем абсолютный URL до картинки
        avatar_url = request.build_absolute_uri(user.avatar.url) if user.avatar else None
        return Response({'avatar': avatar_url})