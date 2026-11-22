import logging
import uuid
from datetime import timedelta

from django.utils import timezone
from django_q.tasks import async_task

from booking_app.models import Booking, SMSTemplate, Client
from booking_app.sms_service import send_sms
from cabinet_app.services.push import send_bulk_push_to_clients
from notify_app.services.dispatcher import is_notification_allowed

logger = logging.getLogger(__name__)


# ==========================================
# ВОРКЕРЫ ДЛЯ МАССОВЫХ РАССЫЛОК
# ==========================================

def worker_send_broadcast(
    title: str, 
    body: str, 
    methods: list, 
    type_code: str = 'marketing', 
    action_url: str = '/cabinet/', 
    client_ids: list = None
):
    """Фоновая задача для массовой рассылки."""
    logger.info(f"🚀 Запуск рассылки '{title}' каналами {methods}")
    
    if client_ids is None:
        clients = Client.objects.filter(cabinet_user__isnull=False).distinct()
    else:
        clients = Client.objects.filter(id__in=client_ids)
    
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
        
        if 'push' in methods:
            send_bulk_push_to_clients(chunk, title, body, action_url)
            
        if 'sms' in methods:
            for cid in chunk:
                client = Client.objects.get(id=cid)
                if client.phone:
                    send_sms(client.phone, f"{title}\n\n{body}")


# ==========================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================

def get_formatted_text(booking, template_key):
    """Берет шаблон из старой таблицы SMSTemplate."""
    try:
        template = SMSTemplate.objects.get(key=template_key)
    except SMSTemplate.DoesNotExist:
        logger.error(f"❌ Шаблон SMS '{template_key}' не найден в БД!")
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


# ==========================================
# ВОРКЕРЫ ДЛЯ СИСТЕМНЫХ УВЕДОМЛЕНИЙ
# ==========================================

def worker_send_event(booking_id, event_type):
    """Отправка SMS и Push о событиях записи (creation, cancel, edit)."""
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return

    text = get_formatted_text(booking, event_type)
    
    if text:
        if booking.phone:
            send_sms(booking.phone, text)
            
        if booking.client_id:
            # Внутренний вызов пуша (напрямую, без async_task, так как мы уже в фоне)
            send_bulk_push_to_clients(
                [booking.client_id],
                'Статус записи изменен',
                text,
                '/cabinet/appointments'
            )


def worker_send_reminder(booking_id, timeframe):
    """Отправка напоминаний (24h, 2h, 15m)."""
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
    
    if text:
        if booking.phone:
            send_sms(booking.phone, text)
            
        if booking.client_id:
            send_bulk_push_to_clients(
                [booking.client_id],
                'Напоминание о визите',
                text,
                '/cabinet/appointments'
            )
        
        setattr(booking, flag_name, True)
        booking.save(update_fields=[flag_name])


def worker_send_review_request(booking_id):
    """Отправка просьбы об отзыве."""
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return

    if not booking.review_token:
        booking.review_token = uuid.uuid4()
        booking.save()

    url_for_sms = f"https://sasha-sugar.ru/review/{booking.review_token}/"
    sms_text = f"Здравствуйте, {booking.client_name}! Спасибо, что посетили Sasha Sugar. Будем рады, если вы поделитесь впечатлениями: {url_for_sms}"
    
    if booking.phone:
        send_sms(booking.phone, sms_text)
        
    if booking.client_id:
        send_bulk_push_to_clients(
            [booking.client_id],
            'Спасибо за визит!',
            'Будем рады, если вы оцените наш сервис.',
            f'/cabinet/reviews/{booking.review_token}'
        )


# ==========================================
# ВОРКЕРЫ ДЛЯ АДМИНОВ (ЗАДЕЛ НА БУДУЩЕЕ)
# ==========================================

def worker_admin_new_booking(booking_id):
    """FCM-пуш админу о новой записи."""
    # Здесь будет вызов старой функции send_fcm_notification для админов
    pass

def worker_admin_new_review(review_id):
    """FCM-пуш админу о новом отзыве."""
    pass