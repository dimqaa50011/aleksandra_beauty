import logging
from datetime import timedelta
from django.utils import timezone
from django_q.tasks import async_task

from .models import Booking, SMSTemplate
from .sms_service import send_sms

logger = logging.getLogger(__name__)


def get_formatted_text(booking, template_key):
    """
    Берет шаблон из БД и подставляет данные (имя, время, услуги).
    Поддерживаемые переменные: {name}, {date}, {date_full}, {time}, {services}, {address}
    """
    try:
        template = SMSTemplate.objects.get(key=template_key)
    except SMSTemplate.DoesNotExist:
        logger.error(f"❌ Шаблон SMS '{template_key}' не найден в БД!")
        return None

    # 1. Достаем список услуг и склеиваем их через запятую
    services = booking.services.all()
    services_text = ", ".join([s.name for s in services]) if services else "процедуры"

    # 2. Подставляем данные в шаблон
    try:
        return template.text.format(
            name=booking.client_name,
            date=booking.appointment_datetime.strftime('%d.%m'),
            date_full=booking.appointment_datetime.strftime('%d %B'),
            time=booking.appointment_datetime.strftime('%H:%M'),
            services=services_text,
            address="Спасский пер., 7"
        )
    except KeyError as e:
        logger.error(f"❌ Ошибка в шаблоне '{template_key}': неизвестная переменная {e}")
        # Если в шаблоне опечатка, возвращаем текст как есть, чтобы SMS ушла
        return template.text


def send_event_sms_task(booking_id, event_type):
    """
    Задача для отправки событийных SMS: creation, edit, cancel.
    Вызывается через async_task.
    """
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        logger.warning(f"Запись {booking_id} не найдена. SMS '{event_type}' отменена.")
        return

    text = get_formatted_text(booking, event_type)
    if text:
        send_sms(booking.phone, text)


def send_reminder_task(booking_id, timeframe):
    """
    Задача для отправки напоминаний: 24h, 2h, 15m.
    Вызывается через async_task с отложенным запуском (schedule).
    """
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return

    # 1. Проверка статуса (если админ отменил запись)
    if booking.status != 'confirmed':
        logger.info(f"Запись {booking_id} не активна. Напоминание {timeframe} не отправлено.")
        return

    # 2. Проверка флага (если уже отправляли)
    flag_name = f'reminded_{timeframe}'
    if getattr(booking, flag_name):
        logger.info(f"Напоминание {timeframe} для записи {booking_id} уже было отправлено.")
        return

    # 3. Проверка времени (защита от переносов)
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
        logger.info(f"Время для напоминания {timeframe} не совпадает (возможно, запись перенесли).")
        return

    # 4. Отправка и сохранение флага
    text = get_formatted_text(booking, f'reminder_{timeframe}')
    if text:
        success = send_sms(booking.phone, text)
        if success:
            setattr(booking, flag_name, True)
            booking.save(update_fields=[flag_name])
            logger.info(f"✅ Отправлено {timeframe} напоминание для {booking.client_name}")


def schedule_reminders(booking_id, appointment_datetime):
    """
    Планирует 3 напоминания для записи.
    Вызывается сразу после создания или изменения записи.
    """
    now = timezone.now()
    
    # 24 часа
    time_24h = appointment_datetime - timedelta(hours=24)
    if time_24h > now:
        async_task(
            'booking_app.tasks.send_reminder_task', 
            booking_id, '24h', 
            schedule=time_24h
        )
        
    # 2 часа
    time_2h = appointment_datetime - timedelta(hours=2)
    if time_2h > now:
        async_task(
            'booking_app.tasks.send_reminder_task', 
            booking_id, '2h', 
            schedule=time_2h
        )
        
    # 15 минут
    time_15m = appointment_datetime - timedelta(minutes=15)
    if time_15m > now:
        async_task(
            'booking_app.tasks.send_reminder_task', 
            booking_id, '15m', 
            schedule=time_15m
        )