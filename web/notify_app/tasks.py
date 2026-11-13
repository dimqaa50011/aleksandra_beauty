import logging
import uuid
from datetime import timedelta

from django.utils import timezone
from django_q.tasks import async_task

from booking_app.models import Booking, SMSTemplate, Client
from cabinet_app.services.push import send_bulk_push_to_clients
from notify_app.services.dispatcher import send_notification, is_notification_allowed

logger = logging.getLogger(__name__)


def task_send_broadcast(type_code: str, title: str, body: str, action_url: str = '/cabinet/'):
    """Фоновая задача для массовой рассылки клиентам."""
    logger.info(f"🚀 Запуск рассылки '{type_code}': {title}")
    
    clients = Client.objects.filter(cabinet_user__isnull=False).distinct()
    
    allowed_ids = []
    for client in clients:
        allowed, _ = is_notification_allowed(client, type_code)
        if allowed:
            allowed_ids.append(client.id)

    total = len(allowed_ids)
    logger.info(f"📊 Найдено {total} клиентов, готовых получить рассылку.")
    
    chunk_size = 500
    for i in range(0, total, chunk_size):
        chunk = allowed_ids[i:i+chunk_size]
        send_bulk_push_to_clients(chunk, title, body, action_url)


def get_formatted_text(booking, template_key):
    try:
        template = SMSTemplate.objects.get(key=template_key)
    except SMSTemplate.DoesNotExist:
        return None

    services = booking.services.all()
    services_text = ", ".join([s.name for s in services]) if services else "процедуры"
    local_dt = timezone.localtime(booking.appointment_datetime)

    try:
        return template.text.format(
            name=booking.client_name,
            date=local_dt.strftime('%d.%m'),
            date_full=local_dt.strftime('%d %B'),
            time=local_dt.strftime('%H:%M'),
            services=services_text,
            address="Спасский пер., 7"
        )
    except KeyError:
        return template.text


def send_event_sms_task(booking_id, event_type):
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return

    text = get_formatted_text(booking, event_type)
    
    if text and booking.client_id:
        type_code = f'booking_{event_type}' 
        
        send_notification(
            client_id=booking.client_id,
            type_code=type_code,
            title='Статус записи изменен',
            push_body=text,
            action_url='/cabinet/appointments',
            sms_text=text
        )


def send_reminder_task(booking_id, timeframe):
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return

    if booking.status != 'confirmed':
        return

    flag_name = f'reminded_{timeframe}'
    if getattr(booking, flag_name):
        return

    now = timezone.now()
    time_diff = booking.appointment_datetime - now
    is_time_correct = False
    
    if timeframe == '24h' and timedelta(hours=23.5) <= time_diff <= timedelta(hours=24.5):
        is_time_correct = True
    elif timeframe == '2h' and timedelta(hours=1.5) <= time_diff <= timedelta(hours=2.5):
        is_time_correct = True
    elif timeframe == '15m' and timedelta(minutes=10) <= time_diff <= timedelta(minutes=20):
        is_time_correct = True

    if not is_time_correct:
        return

    text = get_formatted_text(booking, f'reminder_{timeframe}')
    
    if text and booking.client_id:
        send_notification(
            client_id=booking.client_id,
            type_code=f'reminder_{timeframe}',
            title='Напоминание о визите',
            push_body=text,
            action_url='/cabinet/appointments',
            sms_text=text
        )
        
        setattr(booking, flag_name, True)
        booking.save(update_fields=[flag_name])


def schedule_reminders(booking_id, appointment_datetime):
    """Планирует 3 напоминания для записи."""
    now = timezone.now()
    
    time_24h = appointment_datetime - timedelta(hours=24)
    if time_24h > now:
        async_task(
            'notify_app.tasks.send_reminder_task', 
            booking_id, '24h', 
            q_options={'schedule': time_24h}
        )
        
    time_2h = appointment_datetime - timedelta(hours=2)
    if time_2h > now:
        async_task(
            'notify_app.tasks.send_reminder_task', 
            booking_id, '2h', 
            q_options={'schedule': time_2h}
        )
        
    time_15m = appointment_datetime - timedelta(minutes=15)
    if time_15m > now:
        async_task(
            'notify_app.tasks.send_reminder_task', 
            booking_id, '15m', 
            q_options={'schedule': time_15m}
        )


def send_review_request_task(booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return

    if not booking.review_token:
        booking.review_token = uuid.uuid4()
        booking.save()

    url = f"https://sasha-sugar.ru/review/{booking.review_token}/"
    
    if booking.client_id:
        send_notification(
            client_id=booking.client_id,
            type_code='review_request',
            title='Спасибо за визит!',
            push_body='Будем рады, если вы оцените наш сервис.',
            action_url=f'/cabinet/reviews/{booking.review_token}',
            sms_text=f"Здравствуйте, {booking.client_name}! Спасибо, что посетили Sasha Sugar. Будем рады, если вы поделитесь впечатлениями: {url}"
        )


def task_send_bulk_push(client_ids: list[int], title: str, body: str, action_url: str = '/cabinet/'):
    send_bulk_push_to_clients(client_ids, title, body, action_url)