import uuid
import json
import re
import requests
import traceback # <-- Для вывода полной ошибки в консоль
from django.conf import settings
from django.core.cache import cache
from .models import PostIdea, PostContent

# Константы API
GIGACHAT_AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGACHAT_CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
TOKEN_CACHE_KEY = "gigachat_access_token"
TOKEN_TTL = 1500  # 25 минут


def get_gigachat_token() -> str:
    """Получает токен из кэша или запрашивает новый у API."""
    token = cache.get(TOKEN_CACHE_KEY)
    if token:
        print("🔑 Токен GigaChat взят из кэша")
        return token

    client_id = getattr(settings, 'GIGACHAT_CLIENT_ID', '')
    client_secret = getattr(settings, 'GIGACHAT_CLIENT_SECRET', '')
    auth_key = getattr(settings, 'GIGACHAT_AUTH_KEY', '')
    
    if not client_id or not client_secret:
        print("❌ ОШИБКА: GIGACHAT_CLIENT_ID или GIGACHAT_CLIENT_SECRET не настроены в settings.py")
        raise ValueError("Отсутствуют учетные данные GigaChat")

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': str(uuid.uuid4()),
        'Authorization': f'Basic {auth_key}'
    }
    
    payload = {'scope': 'GIGACHAT_API_PERS'}

    try:
        print("📡 Запрашиваем новый токен GigaChat...")
        response = requests.post(GIGACHAT_AUTH_URL, headers=headers, data=payload, timeout=10, verify=False)
        response.raise_for_status()
        
        data = response.json()
        access_token = data.get('access_token')
        
        if access_token:
            cache.set(TOKEN_CACHE_KEY, access_token, TOKEN_TTL)
            print("✅ Успешно получен новый токен GigaChat")
            return access_token
        else:
            print(f"❌ Ошибка получения токена: {data}")
            raise Exception("Не удалось получить access_token из ответа API")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса токена GigaChat: {e}")
        raise


def call_gigachat_api(topic: str, description: str) -> dict:
    """Делает запрос к GigaChat и возвращает структурированный ответ."""
    token = get_gigachat_token()
    
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

    try:
        print(f"📡 Отправляем запрос к GigaChat. Тема: {topic}")
        # Увеличили таймаут до 60 секунд, так как нейросети иногда думают долго
        response = requests.post(GIGACHAT_CHAT_URL, headers=headers, json=payload, timeout=60, verify=False)
        
        if not response.ok:
            print(f"❌ GigaChat вернул ошибку {response.status_code}. Ответ: {response.text}")
        response.raise_for_status()
        
        data = response.json()
        raw_content = data['choices'][0]['message']['content']
        print(f"📥 Получен сырой ответ (первые 100 символов): {raw_content[:100]}...")
        
        # Очистка markdown
        cleaned_content = re.sub(r'^```(?:json)?\s*', '', raw_content, flags=re.IGNORECASE | re.MULTILINE)
        cleaned_content = re.sub(r'\s*```$', '', cleaned_content, flags=re.MULTILINE).strip()
        
        # Экранирование переносов
        def escape_newlines_in_json(match):
            return match.group(0).replace('\n', '\\n').replace('\r', '')
        
        cleaned_content = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', escape_newlines_in_json, cleaned_content)
        
        # Парсинг JSON
        result = json.loads(cleaned_content)
        
        if not all(k in result for k in ['headline', 'body', 'hashtags']):
            raise ValueError("API вернул JSON без обязательных полей")
            
        print("✅ JSON успешно распарсен!")
        return result

    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети при запросе к GigaChat API: {e}")
        raise
    except json.JSONDecodeError as e:
        print(f"❌ Не удалось распарсить JSON от GigaChat. Сырой ответ:\n{raw_content}")
        raise
    except Exception as e:
        print(f"❌ Непредвиденная ошибка при генерации: {e}")
        raise


def generate_post_task(idea_id: int):
    """Фоновая задача для генерации поста."""
    print(f"\n{'='*40}")
    print(f"🚀 НАЧАЛО ЗАДАЧИ генерации для идеи #{idea_id}")
    
    try:
        idea = PostIdea.objects.get(id=idea_id)
    except PostIdea.DoesNotExist:
        print(f"❌ ОШИБКА: Идея с id={idea_id} не найдена в базе.")
        return

    print(f"📝 Тема: {idea.topic}")

    try:
        # 1. Запрос к нейросети
        response = call_gigachat_api(idea.topic, idea.description)

        # 2. Сохранение в БД
        post = PostContent.objects.create(
            idea=idea,
            variant_name=f"Вариант {idea.posts.count() + 1}",
            headline=response["headline"],
            body=response["body"],
            hashtags=response["hashtags"],
            is_approved=False,
            is_published=False
        )

        # 3. Обновление статуса
        idea.status = 'in_progress'
        idea.save()

        print(f"✅ УСПЕХ: Пост #{post.id} создан и сохранен в базе!")

    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА при генерации поста #{idea_id}:")
        # Этот принт выведет полный стектрейс (где именно упало)
        traceback.print_exc() 
        
        # Пробрасываем ошибку дальше, чтобы Django-Q покрасил задачу в красный
        raise e
    finally:
        print(f"{'='*40}\n")