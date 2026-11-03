import json
import logging
from pywebpush import webpush, WebPushException
from django.conf import settings
from django.utils import timezone

from ..models import ClientPushSubscription, NotificationLog

logger = logging.getLogger(__name__)

def _send_to_subscription(sub: ClientPushSubscription, payload: dict) -> bool:
    """Отправляет пуш на одно конкретное устройство."""
    try:
        webpush(
            subscription_info={
                'endpoint': sub.endpoint,
                'keys': {'p256dh': sub.p256dh, 'auth': sub.auth}
            },
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={'sub': f'mailto:{settings.VAPID_ADMIN_EMAIL}'},
            headers={'Urgency': 'high'}
        )
        return True
    except WebPushException as e:
        # Если подписка умерла (404 или 410)
        if e.response and e.response.status_code in (404, 410):
            sub.is_active = False
            sub.save(update_fields=['is_active'])
            logger.warning(f"Client push subscription expired for user {sub.user_id}")
        else:
            logger.error(f"WebPush error to client {sub.user_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending push to user {sub.user_id}: {e}")
        return False


def send_bulk_push_to_clients(client_ids: list[int], title: str, body: str, url: str = '/cabinet/'):
    """
    Отправляет пуш-уведомление списку клиентов.
    Создает запись в NotificationLog для каждого клиента.
    """
    if not client_ids:
        return

    payload = {
        'title': title,
        'body': body,
        'url': url
    }

    # Получаем все активные устройства для указанных клиентов
    subscriptions = ClientPushSubscription.objects.filter(
        user__client_id__in=client_ids, 
        is_active=True
    ).select_related('user__client')

    # Группируем подписки по клиентам
    client_subs = {cid: [] for cid in client_ids}
    for sub in subscriptions:
        client_subs[sub.user.client_id].append(sub)

    # Рассылаем
    for client_id, subs in client_subs.items():
        if not subs:
            # У клиента нет подписок, пишем в лог, что пропущено
            log = NotificationLog.objects.create(
                client_id=client_id,
                event_type='broadcast',
                channel=NotificationLog.CHANNEL_PUSH,
                status=NotificationLog.STATUS_SKIPPED,
                payload=payload,
                error='Нет активных подписок на устройствах'
            )
            payload['url'] = f'/cabinet/notifications/{log.id}'
            continue

        success = False
        for sub in subs:
            if _send_to_subscription(sub, payload):
                success = True
        
        # Записываем общий результат для этого клиента
        NotificationLog.objects.create(
            client_id=client_id,
            event_type='broadcast',
            channel=NotificationLog.CHANNEL_PUSH,
            status=NotificationLog.STATUS_SENT if success else NotificationLog.STATUS_FAILED,
            payload=payload,
            sent_at=timezone.now() if success else None,
            error='' if success else 'Ошибка отправки на все устройства'
        )

    logger.info(f"Bulk push finished for clients: {client_ids}")