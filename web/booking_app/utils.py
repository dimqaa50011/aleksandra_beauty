import re
from .models import Client

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