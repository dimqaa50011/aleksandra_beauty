from django_q.tasks import async_task
from datetime import timedelta
from django.utils import timezone


class BaseNotifayer:
    """Базовый класс для всех уведомлений."""
    
    @classmethod
    def _send(cls, task_path: str, *args, **kwargs):
        """
        Отправляет задачу в очередь Django-Q.
        task_path: путь до функции воркера (например, 'notify_app.tasks.worker_...')
        """
        async_task(task_path, *args, **kwargs)


class ClientNotify(BaseNotifayer):
    """Уведомления для клиентов (СМС + PWA Push)."""

    @classmethod
    def broadcast(cls, title: str, body: str, methods: list, type_code: str = 'marketing', action_url: str = '/cabinet/', client_ids: list = None):
        """Массовая рассылка (маркетинг)."""
        cls._send(
            'notify_app.tasks.worker_send_broadcast',
            title, body, methods, type_code, action_url, client_ids
        )

    @classmethod
    def booking_event(cls, booking_id: int, event_type: str):
        """Уведомление о статусе записи (creation, cancel, edit)."""
        cls._send(
            'notify_app.tasks.worker_send_event',
            booking_id, event_type
        )
    
    @classmethod
    def edit_booking(cls,  booking_id: int,):
        cls._send('notify_app.tasks.send_event_sms_task', booking_id, 'edit')

    @classmethod
    def schedule_reminders(cls, booking_id: int, appointment_datetime):
        """Планирует 3 напоминания (24ч, 2ч, 15м) для записи."""
        now = timezone.now()
        
        time_24h = appointment_datetime - timedelta(hours=24)
        if time_24h > now:
            cls._send('notify_app.tasks.worker_send_reminder', booking_id, '24h', q_options={'schedule': time_24h})
            
        time_2h = appointment_datetime - timedelta(hours=2)
        if time_2h > now:
            cls._send('notify_app.tasks.worker_send_reminder', booking_id, '2h', q_options={'schedule': time_2h})
            
        time_15m = appointment_datetime - timedelta(minutes=15)
        if time_15m > now:
            cls._send('notify_app.tasks.worker_send_reminder', booking_id, '15m', q_options={'schedule': time_15m})

    @classmethod
    def review_request(cls, booking_id: int):
        """Запрос отзыва после визита."""
        cls._send('notify_app.tasks.worker_send_review_request', booking_id)


class AdminNotify(BaseNotifayer):
    """Уведомления для админов (FCM Push в мобильное приложение)."""

    @classmethod
    def new_booking(cls, booking_id: int):
        """Оповещение админа о новой записи."""
        # Здесь мы вызываем воркер, который делает FCM-пуш админу
        cls._send('notify_app.tasks.worker_admin_new_booking', booking_id)

    @classmethod
    def new_review(cls, review_id: int):
        """Оповещение админа о новом отзыве."""
        cls._send('notify_app.tasks.worker_admin_new_review', review_id)