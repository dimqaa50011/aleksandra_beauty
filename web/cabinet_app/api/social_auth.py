from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from booking_app.models import Client # <--- ВАЖНЫЙ ИМПОРТ
from ..models import CabinetUser, ClientRefreshToken
from ..authentication import issue_access_token
from ..services.social_auth import validate_telegram_data, validate_max_data, validate_vk_data
from .auth import _auth_response, _client_ip, _platform


class SocialAuthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, platform):
        data = request.data
        user_data = None

        try:
            if platform == 'telegram':
                user_data = validate_telegram_data(data.get('init_data', ''))
                platform_id = str(user_data['id'])
                lookup = {'telegram_id': platform_id}
            elif platform == 'max':
                user_data = validate_max_data(data.get('init_data', ''))
                platform_id = str(user_data['id'])
                lookup = {'max_id': platform_id}
            elif platform == 'vk':
                user_data = validate_vk_data(data.get('launch_params', {}))
                platform_id = str(user_data['id'])
                lookup = {'vk_id': platform_id}
            else:
                return Response({'error': 'Unknown platform'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Ищем или создаем пользователя
        user = CabinetUser.objects.filter(**lookup).first()
        is_new = False

        if not user:
            is_new = True
            
            # 1. Создаем временного клиента в CRM
            name = user_data.get('first_name', '')
            last_name = user_data.get('last_name', '')
            full_name = f"{name} {last_name}".strip() or f"Гость {platform}"
            
            # Генерируем временный телефон, чтобы не нарушать уникальность
            dummy_phone = f"{platform}_{platform_id}"
            
            temp_client = Client.objects.create(
                phone=dummy_phone,
                name=full_name
            )

            # 2. Создаем аккаунт и привязываем к временному клиенту
            user = CabinetUser(**lookup)
            user.client = temp_client
            user.set_unusable_password() # Пароля пока нет!
            user.save()

        # Выдаем токены
        access = issue_access_token(user)
        _, refresh_raw = ClientRefreshToken.issue(
            user, 
            user_agent=request.META.get('HTTP_USER_AGENT', ''), 
            platform=platform
        )

        resp = _auth_response(user, access, refresh_raw)
        resp.data['is_new'] = is_new
        return resp