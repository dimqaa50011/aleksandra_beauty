import logging
from notify_app.models import NotificationType, ClientNotificationSetting
from booking_app.models import Client
from django_q.tasks import async_task

logger = logging.getLogger(__name__)

def is_notification_allowed(client: Client, type_code: str) -> tuple[bool, NotificationType]:
    """Возвращает (разрешено_ли_клиентом, объект_типа)."""
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


def send_notification(
    client_id: int, 
    type_code: str, 
    title: str, 
    push_body: str, 
    action_url: str = '/cabinet/',
    sms_text: str = None
):
    """
    Универсальный метод отправки.
    Смотрит на настройки клиента и флаги каналов в NotificationType.
    """
    try:
        client = Client.objects.get(pk=client_id)
    except Client.DoesNotExist:
        return

    allowed_by_client, n_type = is_notification_allowed(client, type_code)
    
    if not allowed_by_client:
        logger.info(f"Клиент {client_id} отключил уведомления типа {type_code}. Пропускаем.")
        return

    # 1. Отправляем Push (если разрешено в типе)
    if n_type.allow_push:
        async_task(
            'notify_app.tasks.task_send_bulk_push',
            [client_id],
            title,
            push_body,
            action_url
        )

    # 2. Отправляем SMS (если разрешено в типе и передан текст)
    if n_type.allow_sms and sms_text and client.phone:
        from booking_app.sms_service import send_sms
        async_task(send_sms, client.phone, sms_text)