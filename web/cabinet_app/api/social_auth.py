import hashlib
import hmac
import json
import base64
import logging
from urllib.parse import urlencode, parse_qsl

from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from booking_app.models import Client
from ..models import CabinetUser, ClientRefreshToken
from ..authentication import issue_access_token
from .auth import _auth_response

logger = logging.getLogger(__name__)


# ==========================================
# ВАЛИДАЦИЯ ДАННЫХ
# ==========================================

def validate_telegram_data(init_data: str) -> dict:
    """Проверяет подпись Telegram WebApp."""
    try:
        parsed_data = dict(parse_qsl(init_data))
        hash_str = parsed_data.pop('hash', None)
        if not hash_str:
            raise ValueError('No hash provided')

        data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(parsed_data.items()))
        secret_key = hmac.new(b"WebAppData", settings.TELEGRAM_BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if calculated_hash != hash_str:
            raise ValueError('Invalid signature')

        return json.loads(parsed_data.get('user', '{}'))
    except Exception as e:
        raise ValueError(f'Invalid Telegram data: {str(e)}')


def validate_max_data(init_data: str) -> dict:
    """Проверяет подпись MAX (схема аналогична TG)."""
    try:
        parsed_data = dict(parse_qsl(init_data))
        hash_str = parsed_data.pop('hash', None)
        if not hash_str:
            raise ValueError('No hash provided')

        data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(parsed_data.items()))
        secret_key = hmac.new(b"WebAppData", settings.MAX_BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if calculated_hash != hash_str:
            raise ValueError('Invalid signature')

        return json.loads(parsed_data.get('user', '{}'))
    except Exception as e:
        raise ValueError(f'Invalid MAX data: {str(e)}')


def validate_vk_data(launch_params: dict) -> dict:
    """Безопасная проверка подписи VK."""
    try:
        params = launch_params.copy()
        sign = params.pop('sign', None)
        if not sign:
            raise ValueError('No sign provided')

        # Оставляем только vk_ параметры
        vk_params = {k: v for k, v in params.items() if k.startswith('vk_')}
        if not vk_params:
            raise ValueError('No vk_ params')

        # Проверка ID приложения
        if str(vk_params.get('vk_app_id')) != str(settings.VK_APP_ID):
            raise ValueError('Invalid vk_app_id')

        # Проверка времени (подпись не должна быть старше 1 часа)
        vk_ts = int(vk_params.get('vk_ts', 0))
        if timezone.now().timestamp() - vk_ts > 3600:
            raise ValueError('Signature expired')

        # Формируем строку для проверки
        query_string = urlencode(sorted(vk_params.items()))
        secret_key = settings.VK_APP_SECRET.encode()
        
        # Считаем HMAC-SHA256 и переводим в base64url без паддинга
        calculated_hash = hmac.new(secret_key, query_string.encode(), hashlib.sha256).digest()
        calculated_sign = base64.urlsafe_b64encode(calculated_hash).decode().rstrip('=')

        if calculated_sign != sign:
            raise ValueError('Invalid signature')

        return {
            'id': str(vk_params['vk_user_id']),
            'first_name': vk_params.get('vk_first_name', ''),
            'last_name': vk_params.get('vk_last_name', ''),
        }
    except Exception as e:
        raise ValueError(f'Invalid VK data: {str(e)}')


# ==========================================
# ОБЩАЯ ЛОГИКА АВТОРИЗАЦИИ
# ==========================================

class SocialAuthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, platform):
        data = request.data
        user_data = None

        try:
            if platform == 'telegram':
                user_data = validate_telegram_data(data.get('init_data', ''))
                lookup = {'telegram_id': str(user_data['id'])}
            elif platform == 'max':
                user_data = validate_max_data(data.get('init_data', ''))
                lookup = {'max_id': str(user_data['id'])}
            elif platform == 'vk':
                user_data = validate_vk_data(data.get('launch_params', {}))
                lookup = {'vk_id': str(user_data['id'])}
            else:
                return Response({'error': 'Unknown platform'}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Ищем или создаем пользователя
        user = CabinetUser.objects.filter(**lookup).first()
        is_new = False

        if not user:
            is_new = True
            
            # Создаем временного клиента для CRM
            name = user_data.get('first_name', '')
            last_name = user_data.get('last_name', '')
            full_name = f"{name} {last_name}".strip() or f"Гость {platform}"
            
            # Генерируем временный телефон, чтобы не нарушать уникальность
            dummy_phone = f"{platform}_{user_data['id']}"
            
            temp_client = Client.objects.create(
                phone=dummy_phone,
                name=full_name
            )

            # Создаем аккаунт и привязываем к временному клиенту
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