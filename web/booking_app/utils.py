import re
from .models import Client

import re


def normalize_phone(raw: str) -> str:
    """Возвращает '7XXXXXXXXXX' или '' если номер битый."""
    if not raw:
        return ''
    digits = re.sub(r'\D', '', raw)
    if len(digits) == 11 and digits[0] in ('7', '8'):
        return '7' + digits[1:]
    if len(digits) == 10:
        return '7' + digits
    return ''


def phone_variants(raw: str) -> list[str]:
    """Возможные формы записи этого номера в БД (для filter(phone__in=...))."""
    if not raw:
        return []
    digits = re.sub(r'\D', '', raw)
    if not digits:
        return [raw]

    variants = {raw, digits, '+' + digits}
    if len(digits) == 11 and digits[0] in ('7', '8'):
        core = digits[1:]
        variants.update({
            f'7{core}', f'8{core}',
            f'+7{core}', f'+8{core}',
            f'+7 ({core[:3]}) {core[3:6]}-{core[6:8]}-{core[8:]}',
            f'8 ({core[:3]}) {core[3:6]}-{core[6:8]}-{core[8:]}',
            f'8-{core[:3]}-{core[3:6]}-{core[6:8]}-{core[8:]}',
        })
    elif len(digits) == 10:
        variants.update({
            f'7{digits}', f'8{digits}',
            f'+7{digits}', f'+8{digits}',
        })
    return list(variants)

def find_client_by_phone(raw: str):
    """Ищет Client по любому варианту записи телефона."""
    return Client.objects.filter(phone__in=phone_variants(raw)).first()


def find_client_candidates(raw: str):
    """Все совпадения — на случай, если в БД уже есть дубли по формату."""
    return Client.objects.filter(phone__in=phone_variants(raw))

def get_or_create_client(phone, name="", email=""):
    """
    Ищет клиента по номеру телефона.
    Если находит, обновляет имя/email (если они были пустые).
    Если не находит, создает нового.
    """
    # 1. Очищаем телефон от пробелов и скобок для надежного поиска
    clean_phone = re.sub(r'[^\d+]', '', phone)
    
    if not clean_phone:
        return None

    # 2. Ищем клиента
    client = Client.objects.filter(phone=clean_phone).first()

    if client:
        # Обновляем данные, если они были пустые, а теперь появились
        updated = False
        if not client.name and name:
            client.name = name
            updated = True
        if not client.email and email:
            client.email = email
            updated = True
            
        if updated:
            client.save()
        return client
    else:
        # 3. Создаем нового клиента
        new_client = Client.objects.create(
            phone=clean_phone,
            name=name,
            email=email if email else None
        )
        return new_client