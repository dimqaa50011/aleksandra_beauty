import logging
from datetime import date as date_cls, datetime, time as dt_time, timedelta

from django.utils import timezone

from booking_app.models import BlockedSlot, Booking

logger = logging.getLogger(__name__)


# Рабочие параметры студии.
WORK_START = dt_time(9, 0)
WORK_END = dt_time(22, 0)
SLOT_STEP_MINUTES = 30
BUFFER_MINUTES = 10
CLIENT_LEAD_TIME_HOURS = 3  # клиент не может записаться менее чем за 3 часа


def calculate_services_duration(services) -> int:
    """Суммарная длительность услуг в минутах. 60, если ни у одной не задана."""
    total = sum(s.duration for s in services if s.duration)
    return total or 60


def _round_up_to_step(dt: datetime, step_minutes: int) -> datetime:
    """Округляет вверх до ближайшего шага сетки (в локальном часовом поясе)."""
    dt = timezone.localtime(dt)  # <-- ФИКС: переводим в локальное время
    minutes = dt.hour * 60 + dt.minute
    rounded = ((minutes + step_minutes - 1) // step_minutes) * step_minutes
    return dt.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=rounded)

def _is_past_or_within_lead_time(dt: datetime, apply_lead_time: bool) -> bool:
    """Слот в прошлом или ближе CLIENT_LEAD_TIME_HOURS?"""
    now = timezone.now()
    if dt <= now:
        return True
    if apply_lead_time:
        return (dt - now) < timedelta(hours=CLIENT_LEAD_TIME_HOURS)
    return False


def is_slot_free(
    target_datetime: datetime,
    duration_minutes: int,
    *,
    apply_lead_time: bool = False,
) -> bool:
    """
    Точечная проверка: можно ли занять это время на duration_minutes.
    - Пересечение с BlockedSlot и Booking — без буфера.
    - Конец рабочего дня — с буфером.
    - Прошлое/лид-тайм — если apply_lead_time.
    """
    if apply_lead_time and _is_past_or_within_lead_time(target_datetime, True):
        return False

    current_tz = timezone.get_current_timezone()
    target_date = target_datetime.date()
    slot_start = target_datetime
    slot_end = slot_start + timedelta(minutes=duration_minutes)
    slot_end_with_buffer = slot_end + timedelta(minutes=BUFFER_MINUTES)

    # Конец рабочего дня — с буфером
    work_end_dt = timezone.make_aware(
        datetime.combine(target_date, WORK_END), current_tz,
    )
    if slot_end_with_buffer > work_end_dt:
        return False

    if slot_start.time() < WORK_START:
        return False

    if BlockedSlot.objects.filter(date=target_date, is_full_day=True).exists():
        return False

    for blocked in BlockedSlot.objects.filter(date=target_date).exclude(start_time__isnull=True):
        b_start = timezone.make_aware(datetime.combine(target_date, blocked.start_time), current_tz)
        b_end = timezone.make_aware(datetime.combine(target_date, blocked.end_time), current_tz)
        if slot_start < b_end and slot_end > b_start:
            return False

    for booking in Booking.objects.filter(
        appointment_datetime__date=target_date,
        status__in=['pending', 'confirmed'],
    ).prefetch_related('services'):
        b_duration = sum(s.duration for s in booking.services.all() if s.duration) or 30
        b_start = booking.appointment_datetime
        b_end = b_start + timedelta(minutes=b_duration)
        if slot_start < b_end and slot_end > b_start:
            return False

    return True


def get_available_slots(
    target_date: date_cls,
    duration_minutes: int,
    *,
    apply_lead_time: bool = False,
) -> dict:
    """
    Свободные слоты на дату.
    Возвращает {'times': [...], 'is_blocked': bool, 'total_duration': int}.
    """
    current_tz = timezone.get_current_timezone()

    if BlockedSlot.objects.filter(date=target_date, is_full_day=True).exists():
        return {'times': [], 'is_blocked': True, 'total_duration': duration_minutes}

    if apply_lead_time and target_date < timezone.localdate():
        return {'times': [], 'is_blocked': False, 'total_duration': duration_minutes}

    # Начало перебора
    start_dt = timezone.make_aware(
        datetime.combine(target_date, WORK_START), current_tz,
    )
    if apply_lead_time and target_date == timezone.localdate():
        min_start = _round_up_to_step(
            timezone.now() + timedelta(hours=CLIENT_LEAD_TIME_HOURS),
            SLOT_STEP_MINUTES,
        )
        if min_start > start_dt:
            start_dt = min_start

    work_end_dt = timezone.make_aware(
        datetime.combine(target_date, WORK_END), current_tz,
    )

    # Собираем занятые интервалы один раз
    busy = []

    for blocked in BlockedSlot.objects.filter(date=target_date).exclude(start_time__isnull=True):
        busy.append((
            timezone.make_aware(datetime.combine(target_date, blocked.start_time), current_tz),
            timezone.make_aware(datetime.combine(target_date, blocked.end_time), current_tz),
        ))

    for booking in Booking.objects.filter(
        appointment_datetime__date=target_date,
        status__in=['pending', 'confirmed'],
    ).prefetch_related('services'):
        b_duration = sum(s.duration for s in booking.services.all() if s.duration) or 30
        b_start = booking.appointment_datetime
        busy.append((b_start, b_start + timedelta(minutes=b_duration)))

    available = []
    current = start_dt
    step = timedelta(minutes=SLOT_STEP_MINUTES)

    while current < work_end_dt:
        slot_end = current + timedelta(minutes=duration_minutes)
        slot_end_with_buffer = slot_end + timedelta(minutes=BUFFER_MINUTES)

        if slot_end_with_buffer > work_end_dt:
            break

        overlaps = any(current < b_end and slot_end > b_start for b_start, b_end in busy)
        if not overlaps:
            available.append(current.strftime('%H:%M'))

        current += step

    return {
        'times': available,
        'is_blocked': False,
        'total_duration': duration_minutes + BUFFER_MINUTES,
    }