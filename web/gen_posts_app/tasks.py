import logging
import uuid
import base64
import json
import re
import requests
from django.conf import settings
from django.core.cache import cache
from .models import PostIdea, PostContent

logger = logging.getLogger(__name__)

# Константы API
GIGACHAT_AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGACHAT_CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
TOKEN_CACHE_KEY = "gigachat_access_token"
TOKEN_TTL = 1500  # 25 минут (1500 секунд) с запасом


def get_gigachat_token() -> str:
    """Получает токен из кэша или запрашивает новый у API."""
    # 1. Проверяем кэш
    token = cache.get(TOKEN_CACHE_KEY)
    if token:
        return token

    # 2. Токена нет, запрашиваем новый
    client_id = getattr(settings, 'GIGACHAT_CLIENT_ID', '')
    client_secret = getattr(settings, 'GIGACHAT_CLIENT_SECRET', '')
    token = getattr(settings, 'GIGACHAT_AUTH_KEY', '')
    
    if not client_id or not client_secret:
        logger.error("GIGACHAT_CLIENT_ID или GIGACHAT_CLIENT_SECRET не настроены в settings.py")
        raise ValueError("Отсутствуют учетные данные GigaChat")

    # Формируем Basic Auth заголовок (base64 от client_id:client_secret)
    auth_string = f"{client_id}:{client_secret}"
    encoded_auth = token
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': str(uuid.uuid4()),
        'Authorization': f'Basic {encoded_auth}'
    }
    
    payload = {
        'scope': 'GIGACHAT_API_PERS'
    }

    try:
        # verify=False иногда нужен для сертификатов Сбера, но попробуем стандартный запрос
        # Если будет ошибка SSL, раскомментируй verify=False
        response = requests.post(GIGACHAT_AUTH_URL, headers=headers, data=payload, timeout=10, verify=False)
        response.raise_for_status()
        
        data = response.json()
        access_token = data.get('access_token')
        
        if access_token:
            # Сохраняем в кэш на 25 минут
            cache.set(TOKEN_CACHE_KEY, access_token, TOKEN_TTL)
            logger.info("✅ Успешно получен новый токен GigaChat")
            return access_token
        else:
            logger.error(f"Ошибка получения токена: {data}")
            raise Exception("Не удалось получить access_token из ответа API")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка запроса токена GigaChat: {e}")
        raise


def call_gigachat_api(topic: str, description: str) -> dict:
    """Делает запрос к GigaChat и возвращает структурированный ответ."""
    
    token = get_gigachat_token()
    
    # УЛУЧШЕННЫЙ ПРОМПТ с жестким запретом на реальные переносы строк в JSON
    system_prompt = (
        "Ты — профессиональный SMM-менеджер уютной бьюти-студии 'Sasha Sugar' в Санкт-Петербурге. "
        "Твоя задача — написать вовлекающий пост на основе темы и описания. "
        "Тон: дружелюбный, заботливый, профессиональный. "
        "Обязательно упомяни адрес: Спасский переулок, 7. "
        "В конце добавь призыв к действию. "
        "ОТВЕТЬ СТРОГО В ФОРМАТЕ JSON. "
        "ВАЖНО: Внутри строковых значений JSON НЕ ИСПОЛЬЗУЙ реальные переносы строк (Enter). "
        "Вместо них используй символы \\n. Иначе твой ответ будет невалидным JSON и сломает систему."
        "Формат JSON:\n"
        "{\n"
        '  "headline": "Короткий цепляющий заголовок с 1-2 эмодзи",\n'
        '  "body": "Основной текст поста. Для разделения абзацев используй символы \\n\\n",\n'
        '  "hashtags": "5-7 релевантных хештегов через пробел, начиная с #sashasugar"\n'
        "}"
    )
    
    user_prompt = f"Тема поста: {topic}\nКонтекст и важные детали: {description}"

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    payload = {
        "model": "GigaChat", 
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1500
    }

    chat_url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

    try:
        response = requests.post(chat_url, headers=headers, json=payload, timeout=30, verify=False)
        
        if not response.ok:
            logger.error(f"❌ GigaChat вернул ошибку {response.status_code}. Ответ: {response.text}")
        response.raise_for_status()
        
        data = response.json()
        raw_content = data['choices'][0]['message']['content']
        
        # 1. Убираем markdown-обертки ```json ... ```
        cleaned_content = re.sub(r'^```(?:json)?\s*', '', raw_content, flags=re.IGNORECASE | re.MULTILINE)
        cleaned_content = re.sub(r'\s*```$', '', cleaned_content, flags=re.MULTILINE).strip()
        
        # 2. МАГИЧЕСКОЕ ИСПРАВЛЕНИЕ: заменяем реальные переносы строк внутри кавычек на \n
        # Это спасает от ошибки "Invalid control character", если модель все равно вставила Enter
        def escape_newlines_in_json(match):
            return match.group(0).replace('\n', '\\n').replace('\r', '')
        
        cleaned_content = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', escape_newlines_in_json, cleaned_content)
        
        # 3. Парсим JSON
        result = json.loads(cleaned_content)
        
        if not all(k in result for k in ['headline', 'body', 'hashtags']):
            raise ValueError("API вернул JSON без обязательных полей")
            
        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка сети при запросе к GigaChat API: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Не удалось распарсить JSON от GigaChat. Сырой ответ:\n{raw_content}")
        raise
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при генерации: {e}")
        raise

def generate_post_task(idea_id: int):
    """Фоновая задача для генерации поста."""
    try:
        idea = PostIdea.objects.get(id=idea_id)
    except PostIdea.DoesNotExist:
        logger.error(f"Ошибка: Идея с id={idea_id} не найдена.")
        return

    logger.info(f"🚀 Начинаем генерацию поста для идеи #{idea_id}: {idea.topic}")

    try:
        # 1. Делаем реальный запрос к нейросети
        response = call_gigachat_api(idea.topic, idea.description)

        # 2. Сохраняем сгенерированный контент
        post = PostContent.objects.create(
            idea=idea,
            variant_name=f"Вариант {idea.posts.count() + 1}",
            headline=response["headline"],
            body=response["body"],
            hashtags=response["hashtags"],
            is_approved=False,
            is_published=False
        )

        # 3. Обновляем статус идеи
        idea.status = 'in_progress'
        idea.save()

        logger.info(f"✅ Пост #{post.id} успешно создан для идеи #{idea_id}")

    except Exception as e:
        logger.error(f"❌ Ошибка при генерации поста для идеи #{idea_id}: {str(e)}", exc_info=True)
        # При ошибке статус идеи не меняем, чтобы можно было попробовать снова