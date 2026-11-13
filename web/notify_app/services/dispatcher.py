import logging
from notify_app.models import NotificationType, ClientNotificationSetting
from booking_app.models import Client

logger = logging.getLogger(__name__)

def is_notification_allowed(client: Client, type_code: str) -> tuple[bool, NotificationType]:
    """Проверяет, разрешил ли клиент этот тип уведомлений (для маркетинга)."""
    try:
        n_type = NotificationType.objects.get(code=type_code, is_active=True)
    except NotificationType.DoesNotExist:
        logger.warning(f"Тип уведомления {type_code} не найден или отключен.")
        return False, None

    setting = ClientNotificationSetting.objects.filter(
        client=client, notification_type=n_type
    ).first()

    if setting is not None:
        return setting.is_enabled, n_type
        
    return n_type.default_enabled, n_type