import os
import requests
import logging

logger = logging.getLogger(__name__)

def send_sms(phone, text):
    """Отправляет SMS через шлюз. Возвращает True/False."""
    url = os.getenv("SMS_GATEWAY_URL")
    user = os.getenv("SMS_GATEWAY_USER")
    password = os.getenv("SMS_GATEWAY_PASS")

    if not all([url, user, password]):
        logger.error("❌ Настройки SMS-шлюза не заданы в .env")
        return False

    clean_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    payload = {
        "textMessage": {"text": text},
        "phoneNumbers": [clean_phone]
    }

    try:
        response = requests.post(url, auth=(user, password), json=payload, timeout=10)
        if response.status_code in [200, 201, 202]:
            logger.info(f"✅ SMS отправлена на {clean_phone}")
            return True
        else:
            logger.error(f"❌ Ошибка SMS: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка соединения с SMS-шлюзом: {e}")
        return False