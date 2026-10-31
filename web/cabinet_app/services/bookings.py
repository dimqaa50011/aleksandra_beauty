import logging

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from booking_app.models import Booking
from beauty_app.models import Service
from booking_app.services.slots import calculate_services_duration, is_slot_free
from cert_app.models import CertificateModel

from .bonuses import (
    max_bonuses_for_booking,
    reserve_certificate,
    release_certificate,
)

logger = logging.getLogger(__name__)


CANCEL_MIN_HOURS = 3

CANCEL_REASONS = {
    'sick': 'Болею',
    'plans_changed': 'Планы изменились',
    'cant_make_it': 'Не смогу прийти',
    'other': 'Другое',
}


@transaction.atomic
def create_appointment(
    *,
    user,
    service_ids: list[int],
    appointment_datetime,
    use_bonuses: bool = False,
    bonuses_to_apply: int = 0,
    certificate_id: int | None = None,
) -> Booking:
    client = user.client

    if appointment_datetime <= timezone.now():
        raise ValidationError({'appointment_datetime': 'Дата записи должна быть в будущем'})

    services = list(Service.objects.filter(id__in=service_ids, is_active=True))
    if len(services) != len(set(service_ids)):
        raise ValidationError({'service_ids': 'Некоторые услуги недоступны'})

    duration = calculate_services_duration(services)

    if not is_slot_free(appointment_datetime, duration, apply_lead_time=True):
        raise ValidationError({'appointment_datetime': 'Это время уже занято или недоступно'})

    booking = Booking.objects.create(
        client=client,
        client_name=client.name or user.phone,
        phone=client.phone,
        email=client.email or '',
        appointment_datetime=appointment_datetime,
        status='pending',
        use_bonuses_requested=use_bonuses,
        bonuses_to_apply=bonuses_to_apply if use_bonuses else 0,
    )
    booking.services.set(services)

    if use_bonuses and bonuses_to_apply > 0:
        max_allowed = max_bonuses_for_booking(booking)
        if bonuses_to_apply > max_allowed:
            raise ValidationError({
                'bonuses_to_apply': f'Можно списать не более {max_allowed} бонусов',
            })
        if bonuses_to_apply > client.bonus_balance:
            raise ValidationError({
                'bonuses_to_apply': f'Недостаточно бонусов (баланс {client.bonus_balance})',
            })

    if certificate_id:
        cert = CertificateModel.objects.select_for_update().filter(
            pk=certificate_id, client=client,
        ).first()
        if cert is None:
            raise ValidationError({'certificate_id': 'Сертификат не найден'})
        reserve_certificate(cert, booking)

    logger.info(
        'booking.create id=%s client=%s services=%s datetime=%s bonuses=%s cert=%s',
        booking.pk, client.pk, service_ids, appointment_datetime,
        bonuses_to_apply if use_bonuses else 0, certificate_id,
    )

    # Уведомление админу — как при создании с сайта.
    # Локальный импорт, чтобы не создавать цикл на уровне модулей.
    try:
        from booking_app.views import send_fcm_notification, send_push_notification
        services_names = ", ".join(s.name for s in services)
        send_push_notification(
            '🔔 Новая запись!',
            f'{client.name or user.phone} записался на {services_names}',
            '/admin-dashboard/bookings/',
        )
        send_fcm_notification(
            f'🔔 Новая запись: {client.name or user.phone}',
            f'{services_names}\n{appointment_datetime.strftime("%d.%m %H:%M")}',
            f'/admin-dashboard/bookings/{booking.pk}/edit/',
            booking.id,
        )
    except Exception:
        logger.exception('booking.create notify_admin failed booking=%s', booking.pk)

    # SMS-подтверждение и напоминания — как при создании с сайта
    from django_q.tasks import async_task
    from booking_app.tasks import schedule_reminders
    try:
        async_task('booking_app.tasks.send_event_sms_task', booking.id, 'creation')
        schedule_reminders(booking.id, booking.appointment_datetime)
    except Exception:
        logger.exception('booking.create schedule_reminders failed booking=%s', booking.pk)

    return booking


@transaction.atomic
def cancel_appointment(
    *,
    booking: Booking,
    reason: str,
    reason_text: str = '',
) -> Booking:
    if booking.status not in ('pending', 'confirmed'):
        raise ValidationError('Эту запись нельзя отменить')

    if reason not in CANCEL_REASONS:
        raise ValidationError({'reason': 'Неверная причина отмены'})

    if reason == 'other' and not reason_text.strip():
        raise ValidationError({'reason_text': 'Опишите причину'})

    hours_left = (booking.appointment_datetime - timezone.now()).total_seconds() / 3600
    if hours_left < CANCEL_MIN_HOURS:
        raise ValidationError({
            'detail': f'Отмена возможна не позднее чем за {CANCEL_MIN_HOURS} часа до визита. '
                      f'Позвоните в студию.',
        })

    cert = booking.reserved_certificates.filter(is_used=False).first()
    if cert is not None:
        release_certificate(cert)

    old_status = booking.status
    booking.status = 'cancelled'
    booking.cancel_reason = reason
    booking.cancel_reason_text = reason_text[:255]
    booking.cancelled_by = 'client'
    booking.cancelled_at = timezone.now()
    booking.save(update_fields=[
        'status', 'cancel_reason', 'cancel_reason_text',
        'cancelled_by', 'cancelled_at',
    ])

    logger.info(
        'booking.cancel id=%s client=%s old_status=%s reason=%s cert_released=%s',
        booking.pk, booking.client_id, old_status, reason, cert is not None,
    )

    # SMS клиенту и админу — как при отмене с сайта
    from django_q.tasks import async_task
    try:
        async_task('booking_app.tasks.send_event_sms_task', booking.id, 'cancel')
    except Exception:
        logger.exception('booking.cancel sms failed booking=%s', booking.pk)

    return booking


@transaction.atomic
def reschedule_appointment(
    *,
    booking: Booking,
    new_datetime,
) -> Booking:
    if booking.status not in ('pending', 'confirmed'):
        raise ValidationError('Эту запись нельзя перенести')

    hours_left = (booking.appointment_datetime - timezone.now()).total_seconds() / 3600
    if hours_left < CANCEL_MIN_HOURS:
        raise ValidationError({
            'detail': f'Перенос возможен не позднее чем за {CANCEL_MIN_HOURS} часа. '
                      f'Позвоните в студию.',
        })

    if new_datetime <= timezone.now():
        raise ValidationError({'new_datetime': 'Дата переноса должна быть в будущем'})

    duration = calculate_services_duration(booking.services.all())
    if not is_slot_free(new_datetime, duration, apply_lead_time=True):
        raise ValidationError({'new_datetime': 'Это время уже занято'})

    old_datetime = booking.appointment_datetime
    booking.rescheduled_from = old_datetime
    booking.appointment_datetime = new_datetime
    booking.reminded_24h = False
    booking.reminded_2h = False
    booking.reminded_15m = False
    booking.save(update_fields=[
        'rescheduled_from', 'appointment_datetime',
        'reminded_24h', 'reminded_2h', 'reminded_15m',
    ])

    logger.info(
        'booking.reschedule id=%s client=%s from=%s to=%s',
        booking.pk, booking.client_id, old_datetime, new_datetime,
    )

    from django_q.tasks import async_task
    from booking_app.tasks import schedule_reminders
    try:
        async_task('booking_app.tasks.send_event_sms_task', booking.id, 'edit')
        schedule_reminders(booking.id, booking.appointment_datetime)
    except Exception:
        logger.exception('booking.reschedule notify failed booking=%s', booking.pk)

    return booking