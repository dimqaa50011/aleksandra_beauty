import logging
import uuid
from datetime import timedelta

from django.utils import timezone
from django_q.tasks import async_task

from booking_app.models import Booking, SMSTemplate, Client
from booking_app.sms_service import send_sms
from cabinet_app.services.push import send_bulk_push_to_clients
from notify_app.services.dispatcher import send_notification, is_notification_allowed

logger = logging.getLogger(__name__)


# ==========================================
# МАССОВЫЕ РАССЫЛКИ
# ==========================================

def task_send_broadcast(
    title: str, 
    body: str, 
    methods: list, 
    type_code: str = 'marketing', 
    action_url: str = '/cabinet/', 
    client_ids: list = None
):
    """Фоновая задача для массовой рассылки. Если client_ids=None, отправляет всем."""
    logger.info(f"🚀 Запуск рассылки '{title}' каналами {methods}")
    
    if client_ids is None:
        # Берем всех клиентов, у которых есть аккаунт в PWA
        clients = Client.objects.filter(cabinet_user__isnull=False).distinct()
    else:
        clients = Client.objects.filter(id__in=client_ids)
    
    allowed_ids = []
    for client in clients:
        # Проверяем, не отключил ли клиент этот тип уведомлений
        allowed, _ = is_notification_allowed(client, type_code)
        if allowed:
            allowed_ids.append(client.id)

    total = len(allowed_ids)
    logger.info(f"📊 Найдено {total} клиентов, готовых получить рассылку.")
    
    # Отправляем пачками (chunks), чтобы не перегрузить БД
    chunk_size = 500
    for i in range(0, total, chunk_size):
        chunk = allowed_ids[i:i+chunk_size]
        
        # Отправляем Push
        if 'push' in methods:
            send_bulk_push_to_clients(chunk, title, body, action_url)
            
        # Отправляем SMS
        if 'sms' in methods:
            for cid in chunk:
                client = Client.objects.get(id=cid)
                if client.phone:
                    send_sms(client.phone, f"{title}\n\n{body}")


# ==========================================
# ТРАНЗАКЦИОННЫЕ SMS И УВЕДОМЛЕНИЯ
# ==========================================

def get_formatted_text(booking, template_key):
    """Берет шаблон из БД и подставляет данные."""
    try:
        template = SMSTemplate.objects.get(key=template_key)
    except SMSTemplate.DoesNotExist:
        logger.error(f"❌ Шаблон SMS '{template_key}' не найден в БД!")
        return None

    services = booking.services.all()
    services_text = ", ".join([s.name for s in services]) if services else "процедуры"
    
    # Переводим время из UTC в локальный часовой пояс (Москву)
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
    """Отправка SMS о событиях записи (создание, отмена, перенос)."""
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


# ==========================================
# НАПОМИНАНИЯ
# ==========================================

def send_reminder_task(booking_id, timeframe):
    """Отправка напоминаний (24h, 2h, 15m)."""
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return

    # Проверяем, что запись подтверждена
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
        logger.info(f"Время для напоминания {timeframe} не совпадает. Запись {booking_id}.")
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
        
        # Ставим флаг, что отправили
        setattr(booking, flag_name, True)
        booking.save(update_fields=[flag_name])


def schedule_reminders(booking_id, appointment_datetime):
    """Планирует 3 напоминания для записи."""
    now = timezone.now()
    
    # 24 часа
    time_24h = appointment_datetime - timedelta(hours=24)
    if time_24h > now:
        async_task(
            'notify_app.tasks.send_reminder_task', 
            booking_id, '24h', 
            q_options={'schedule': time_24h}
        )
        
    # 2 часа
    time_2h = appointment_datetime - timedelta(hours=2)
    if time_2h > now:
        async_task(
            'notify_app.tasks.send_reminder_task', 
            booking_id, '2h', 
            q_options={'schedule': time_2h}
        )
        
    # 15 минут
    time_15m = appointment_datetime - timedelta(minutes=15)
    if time_15m > now:
        async_task(
            'notify_app.tasks.send_reminder_task', 
            booking_id, '15m', 
            q_options={'schedule': time_15m}
        )


# ==========================================
# ЗАПРОС ОТЗЫВА
# ==========================================

def send_review_request_task(booking_id):
    """Генерирует ссылку и отправляет SMS + Push с просьбой оставить отзыв."""
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return

    # Генерируем токен, если его нет
    if not booking.review_token:
        booking.review_token = uuid.uuid4()
        booking.save()

    # Ссылка для SMS (старая HTML форма)
    url_for_sms = f"https://sasha-sugar.ru/review/{booking.review_token}/"
    
    if booking.client_id:
        send_notification(
            client_id=booking.client_id,
            type_code='review_request',
            title='Спасибо за визит!',
            push_body='Будем рады, если вы оцените наш сервис.',
            # Ссылка для PWA (внутренний роутинг Vue)
            action_url=f'/cabinet/reviews/{booking.review_token}',
            # Ссылка для SMS
            sms_text=f"Здравствуйте, {booking.client_name}! Спасибо, что посетили Sasha Sugar. Будем рады, если вы поделитесь впечатлениями: {url_for_sms}"
        )


# ==========================================
# ОБЕРТКА ДЛЯ PUSH-УВЕДОМЛЕНИЙ
# ==========================================

def task_send_bulk_push(client_ids: list[int], title: str, body: str, action_url: str = '/cabinet/'):
    send_bulk_push_to_clients(client_ids, title, body, action_url)