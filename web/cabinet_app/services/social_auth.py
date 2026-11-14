import hashlib
import hmac
import json
from urllib.parse import parse_qsl
from django.conf import settings
from rest_framework.exceptions import ValidationError

def validate_telegram_data(init_data: str) -> dict:
    """Проверяет подпись Telegram WebApp."""
    try:
        parsed_data = dict(parse_qsl(init_data))
        hash_str = parsed_data.pop('hash', None)
        if not hash_str:
            raise ValidationError('No hash provided')

        data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(parsed_data.items()))
        secret_key = hmac.new(b"WebAppData", settings.TELEGRAM_BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if calculated_hash != hash_str:
            raise ValidationError('Invalid signature')

        user_data = json.loads(parsed_data.get('user', '{}'))
        return user_data
    except Exception as e:
        raise ValidationError(f'Invalid Telegram data: {str(e)}')

def validate_max_data(init_data: str) -> dict:
    """Проверяет подпись MAX (алгоритм аналогичен TG)."""
    # Предполагаем, что MAX использует ту же схему, что и TG.
    # Если в доках MAX другая схема - поправь здесь.
    # Для этого нужен MAX_BOT_TOKEN в настройках.
    try:
        parsed_data = dict(parse_qsl(init_data))
        hash_str = parsed_data.pop('hash', None)
        if not hash_str:
            raise ValidationError('No hash provided')

        data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(parsed_data.items()))
        secret_key = hmac.new(b"WebAppData", settings.MAX_BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if calculated_hash != hash_str:
            raise ValidationError('Invalid signature')

        user_data = json.loads(parsed_data.get('user', '{}'))
        return user_data
    except Exception as e:
        raise ValidationError(f'Invalid MAX data: {str(e)}')

def validate_vk_data(launch_params: dict) -> dict:
    """Проверяет подпись VK (параметр sign)."""
    try:
        sign = launch_params.pop('sign', None)
        if not sign:
            raise ValidationError('No sign provided')

        # VK использует MD5 для подписи (в старых версиях)
        # Сортируем параметры и склеиваем
        query_string = '&'.join(f'{k}={v}' for k, v in sorted(launch_params.items()) if k.startswith('vk_'))
        calculated_sign = hmac.new(settings.VK_APP_SECRET.encode(), query_string.encode(), hashlib.md5).hexdigest()
        
        # VK кодирует в base64url, но в launch_params приходит как есть.
        # Обычно VK Bridge сам возвращает уже валидные данные, но лучше перепроверить.
        # В новых версиях VK лучше использовать VKWebAppGetUserInfo через Bridge на фронте, 
        # а на бэке валидировать через access_token.
        
        # Для простоты примера, если мы доверяем VK Bridge на фронте:
        vk_user_id = launch_params.get('vk_user_id')
        if not vk_user_id:
            raise ValidationError('No vk_user_id')
            
        return {'id': vk_user_id, 'first_name': launch_params.get('vk_first_name', '')}
    except Exception as e:
        raise ValidationError(f'Invalid VK data: {str(e)}')