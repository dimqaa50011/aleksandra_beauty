import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from booking_app.models import Client, Booking
from cert_app.models import CertificateModel

from ..models import (
    AchievementDefinition,
    BonusTransaction,
    CashbackRule,
    ClientAchievement,
    NotificationLog,
    Referral,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Базовые операции с бонусами
# ─────────────────────────────────────────────────────────────

@transaction.atomic
def accrue_bonuses(
    client: Client,
    amount: int,
    reason: str,
    *,
    booking: Booking | None = None,
    referral: Referral | None = None,
    description: str = '',
    created_by=None,
) -> BonusTransaction | None:
    """Начисляет бонусы. Обновляет Client.bonus_balance."""
    if amount <= 0:
        return None

    locked = Client.objects.select_for_update().get(pk=client.pk)
    old_balance = locked.bonus_balance
    new_balance = old_balance + amount
    locked.bonus_balance = new_balance
    locked.save(update_fields=['bonus_balance'])

    tx = BonusTransaction.objects.create(
        client=locked,
        amount=amount,
        type=BonusTransaction.TYPE_ACCRUAL,
        reason=reason,
        description=(description or '')[:255],
        booking=booking,
        referral=referral,
        balance_after=new_balance,
        created_by=created_by,
    )

    client.bonus_balance = new_balance

    logger.info(
        'bonus.accrue client=%s amount=%s reason=%s balance=%s→%s booking=%s referral=%s',
        locked.pk, amount, reason, old_balance, new_balance,
        booking.pk if booking else None,
        referral.pk if referral else None,
    )
    return tx


@transaction.atomic
def spend_bonuses(
    client: Client,
    amount: int,
    reason: str,
    *,
    booking: Booking | None = None,
    referral: Referral | None = None,
    description: str = '',
    created_by=None,
) -> BonusTransaction | None:
    """Списывает бонусы. Если баланса меньше — списывает сколько есть."""
    if amount <= 0:
        return None

    locked = Client.objects.select_for_update().get(pk=client.pk)
    actual = min(amount, locked.bonus_balance)
    if actual <= 0:
        logger.info(
            'bonus.spend skip client=%s requested=%s balance=0',
            locked.pk, amount,
        )
        return None

    old_balance = locked.bonus_balance
    new_balance = old_balance - actual
    locked.bonus_balance = new_balance
    locked.save(update_fields=['bonus_balance'])

    tx = BonusTransaction.objects.create(
        client=locked,
        amount=-actual,
        type=BonusTransaction.TYPE_SPEND,
        reason=reason,
        description=(description or '')[:255],
        booking=booking,
        referral=referral,
        balance_after=new_balance,
        created_by=created_by,
    )
    client.bonus_balance = new_balance

    log = logger.info if actual == amount else logger.warning
    log(
        'bonus.spend client=%s requested=%s actual=%s reason=%s balance=%s→%s booking=%s',
        locked.pk, amount, actual, reason, old_balance, new_balance,
        booking.pk if booking else None,
    )
    return tx


def get_bonus_balance(client: Client) -> int:
    return client.bonus_balance


# ─────────────────────────────────────────────────────────────
# Лимит и кэшбэк
# ─────────────────────────────────────────────────────────────

def certificate_coverage(booking: Booking) -> Decimal:
    """Сколько из суммы визита покрывает сертификат (если применён)."""
    cert = booking.reserved_certificates.filter(
        is_used=False, reserved_for_booking=booking,
    ).first()
    if cert is None:
        cert = booking.used_certificates.first()
    if cert is None:
        return Decimal('0')

    cert_amount = Decimal(str(cert.price))
    return min(cert_amount, booking.total_price)


def max_bonuses_for_booking(booking: Booking) -> int:
    """Максимум бонусов: 15% от суммы визита за вычетом сертификата."""
    total = booking.total_price
    covered = certificate_coverage(booking)
    base = total - covered
    if base <= 0:
        return 0
    percent = Decimal(str(settings.CABINET_MAX_BONUS_SPEND_PERCENT))
    return int(base * percent / Decimal('100'))


def calculate_cashback(booking: Booking) -> int:
    """
    Кэшбэк: сумма процентов по каждой услуге на дату визита.
    Берём полную стоимость услуги. Округление вниз.
    """
    visit_date = booking.appointment_datetime.date()
    total = 0
    applied_rules = []
    for service in booking.services.all():
        rule = CashbackRule.objects.filter(
            service=service,
            is_active=True,
            valid_from__lte=visit_date,
            valid_until__gte=visit_date,
        ).order_by('-valid_from').first()
        if rule is None:
            continue
        amount = int(service.price * rule.percent / Decimal('100'))
        if amount > 0:
            total += amount
            applied_rules.append(f'{service.pk}:{rule.percent}%')

    logger.info(
        'cashback.calc booking=%s visit_date=%s rules=[%s] total=%s',
        booking.pk, visit_date, ','.join(applied_rules), total,
    )
    return total


# ─────────────────────────────────────────────────────────────
# Сертификаты
# ─────────────────────────────────────────────────────────────

@transaction.atomic
def reserve_certificate(cert: CertificateModel, booking: Booking) -> None:
    """Резервирует сертификат под бронь."""
    if cert.is_used:
        raise ValidationError('Сертификат уже использован')
    if cert.is_expired:
        raise ValidationError('Срок сертификата истёк')
    if cert.reserved_for_booking_id and cert.reserved_for_booking_id != booking.pk:
        raise ValidationError('Сертификат уже зарезервирован под другую запись')

    cert.reserved_for_booking = booking
    cert.save(update_fields=['reserved_for_booking'])
    logger.info('cert.reserve cert=%s booking=%s', cert.pk, booking.pk)


@transaction.atomic
def release_certificate(cert: CertificateModel) -> None:
    """Снимает резерв (при отмене брони)."""
    if cert.is_used:
        return
    old_booking = cert.reserved_for_booking_id
    cert.reserved_for_booking = None
    cert.save(update_fields=['reserved_for_booking'])
    logger.info('cert.release cert=%s booking=%s', cert.pk, old_booking)


@transaction.atomic
def use_certificate(cert: CertificateModel, booking: Booking) -> None:
    """Гасит сертификат полностью. Остаток, если номинал больше суммы — сгорает."""
    if cert.is_used:
        return
    cert.is_used = True
    cert.used_date = timezone.now()
    cert.used_booking = booking
    cert.reserved_for_booking = None
    cert.save(update_fields=[
        'is_used', 'used_date', 'used_booking', 'reserved_for_booking',
    ])
    logger.info(
        'cert.use cert=%s booking=%s face_value=%s visit_total=%s',
        cert.pk, booking.pk, cert.price, booking.total_price,
    )


# ─────────────────────────────────────────────────────────────
# Завершение визита (бонусная часть)
# ─────────────────────────────────────────────────────────────

@transaction.atomic
def apply_bonus_effects(booking: Booking, *, created_by=None) -> dict:
    """
    Бонусная часть завершения визита.
    Статистику клиента (total_bookings, total_spent, last_visit) НЕ трогает —
    её обновляет вызывающий код (AdminBookingStatusAPIView).

    Идемпотентно по Booking.bonuses_processed_at.
    """
    booking = Booking.objects.select_for_update().get(pk=booking.pk)

    if booking.bonuses_processed_at is not None:
        logger.info(
            'bonus.apply skip booking=%s already_processed_at=%s',
            booking.pk, booking.bonuses_processed_at,
        )
        return {}

    if booking.status != 'completed':
        logger.warning(
            'bonus.apply skip booking=%s status=%s (not completed)',
            booking.pk, booking.status,
        )
        return {}

    if booking.client_id is None:
        logger.warning('bonus.apply skip booking=%s no client', booking.pk)
        booking.bonuses_processed_at = timezone.now()
        booking.save(update_fields=['bonuses_processed_at'])
        return {}

    client = booking.client
    result = {
        'bonuses_spent': 0,
        'cashback': 0,
        'certificate_used': False,
        'achievements_unlocked': [],
    }

    logger.info(
        'bonus.apply start booking=%s client=%s total_price=%s '
        'requested_bonuses=%s reserved_cert=%s',
        booking.pk, client.pk, booking.total_price,
        booking.bonuses_to_apply if booking.use_bonuses_requested else 0,
        booking.reserved_certificates.filter(is_used=False).exists(),
    )

    # 1. Списание бонусов
    if booking.use_bonuses_requested and booking.bonuses_to_apply > 0:
        tx = spend_bonuses(
            client,
            booking.bonuses_to_apply,
            reason='visit',
            booking=booking,
            description=f'Оплата бонусами за визит #{booking.pk}',
            created_by=created_by,
        )
        applied = abs(tx.amount) if tx else 0
        booking.bonuses_applied = applied
        result['bonuses_spent'] = applied

    # 2. Гашение сертификата
    cert = booking.reserved_certificates.filter(is_used=False).first()
    if cert is not None:
        use_certificate(cert, booking)
        result['certificate_used'] = True

    # 3. Кэшбэк
    cashback = calculate_cashback(booking)
    if cashback > 0:
        accrue_bonuses(
            client,
            cashback,
            reason='cashback',
            booking=booking,
            description=f'Кэшбэк за визит #{booking.pk}',
            created_by=created_by,
        )
        booking.cashback_accrued = cashback
        result['cashback'] = cashback

    # 4. Рефералка (если клиент — referee и это первый визит)
    _process_referral_first_visit(client, booking, created_by=created_by)

    # 5. Достижения
    unlocked = check_achievements(client)
    result['achievements_unlocked'] = [a.definition.code for a in unlocked]
    if unlocked:
        logger.info(
            'bonus.apply achievements client=%s codes=%s',
            client.pk, result['achievements_unlocked'],
        )

    # 6. Метка идемпотентности
    booking.bonuses_processed_at = timezone.now()
    booking.save(update_fields=[
        'bonuses_processed_at', 'bonuses_applied', 'cashback_accrued',
    ])

    # 7. Уведомление — после коммита, чтобы не откатить бонусы из-за него
    if result['cashback'] > 0:
        transaction.on_commit(
            lambda: _notify_cashback_safe(client.pk, booking.pk, result['cashback']),
        )

    logger.info(
        'bonus.apply done booking=%s spent=%s cashback=%s cert=%s achievements=%s',
        booking.pk, result['bonuses_spent'], result['cashback'],
        result['certificate_used'], result['achievements_unlocked'],
    )
    return result


@transaction.atomic
def handle_booking_cancelled(booking: Booking) -> None:
    """Освобождает резерв сертификата при отмене/неявке."""
    if booking.bonuses_processed_at is not None:
        logger.warning(
            'cancel.skip booking=%s already processed bonuses — '
            'cannot reverse, manual review needed',
            booking.pk,
        )
        return

    cert = booking.reserved_certificates.filter(is_used=False).first()
    if cert is not None:
        release_certificate(cert)
        logger.info('cancel.released_cert booking=%s cert=%s', booking.pk, cert.pk)
    else:
        logger.info('cancel.no_reserved_cert booking=%s', booking.pk)


def _notify_cashback_safe(client_pk: int, booking_pk: int, cashback: int) -> None:
    try:
        _notify_cashback(client_pk, booking_pk, cashback)
    except Exception:
        logger.exception(
            'notify.cashback failed client=%s booking=%s', client_pk, booking_pk,
        )


def _notify_cashback(client_pk: int, booking_pk: int, cashback: int) -> None:
    NotificationLog.objects.create(
        client_id=client_pk,
        booking_id=booking_pk,
        event_type='cashback_accrued',
        channel=NotificationLog.CHANNEL_PUSH,
        status=NotificationLog.STATUS_PENDING,
        payload={
            'title': 'Бонусы начислены',
            'body': f'Вам начислено {cashback} бонусов за визит',
            'url': '/bonuses',
        },
    )


# ─────────────────────────────────────────────────────────────
# Рефералка
# ─────────────────────────────────────────────────────────────

def process_referral_registration(referral: Referral, *, created_by=None) -> None:
    """Малые бонусы при регистрации друга по реф-ссылке."""
    if referral.status != Referral.STATUS_REGISTERED:
        return
    if referral.referrer_id == referral.referee_id:
        logger.warning('referral.self referrer=referee=%s', referral.referrer_id)
        return

    ref_bonus = settings.CABINET_REFERRAL_REGISTER_REFERRER
    friend_bonus = settings.CABINET_REFERRAL_REGISTER_REFEREE

    if ref_bonus > 0:
        accrue_bonuses(
            referral.referrer, ref_bonus, reason='referral_registered',
            referral=referral,
            description=f'Регистрация друга {referral.referee_id}',
            created_by=created_by,
        )
    if friend_bonus > 0:
        accrue_bonuses(
            referral.referee, friend_bonus, reason='referral_registered',
            referral=referral,
            description='Бонус за регистрацию по приглашению',
            created_by=created_by,
        )

    logger.info(
        'referral.register referrer=%s referee=%s ref_bonus=%s friend_bonus=%s',
        referral.referrer_id, referral.referee_id, ref_bonus, friend_bonus,
    )


def _process_referral_first_visit(client: Client, booking: Booking, *, created_by=None) -> None:
    """Крупные бонусы, когда друг впервые завершил визит."""
    referral = Referral.objects.select_for_update().filter(
        referee=client, status=Referral.STATUS_REGISTERED,
    ).first()
    if referral is None:
        return
    if referral.referrer_id == referral.referee_id:
        logger.warning('referral.self_first_visit client=%s', client.pk)
        referral.status = Referral.STATUS_REWARDED
        referral.rewarded_at = timezone.now()
        referral.save(update_fields=['status', 'rewarded_at'])
        return

    referral.status = Referral.STATUS_FIRST_VISIT
    referral.first_visit_at = timezone.now()
    referral.save(update_fields=['status', 'first_visit_at'])

    ref_bonus = settings.CABINET_REFERRAL_FIRST_VISIT_REFERRER
    friend_bonus = settings.CABINET_REFERRAL_FIRST_VISIT_REFEREE

    if ref_bonus > 0:
        accrue_bonuses(
            referral.referrer, ref_bonus, reason='referral_first_visit',
            referral=referral,
            description=f'Друг {client.pk} совершил первый визит',
            created_by=created_by,
        )
    if friend_bonus > 0:
        accrue_bonuses(
            referral.referee, friend_bonus, reason='referral_first_visit',
            referral=referral,
            description='Бонус за первый визит по приглашению',
            created_by=created_by,
        )

    referral.status = Referral.STATUS_REWARDED
    referral.rewarded_at = timezone.now()
    referral.save(update_fields=['status', 'rewarded_at'])

    logger.info(
        'referral.first_visit referrer=%s referee=%s booking=%s '
        'ref_bonus=%s friend_bonus=%s',
        referral.referrer_id, referral.referee_id, booking.pk,
        ref_bonus, friend_bonus,
    )


# ─────────────────────────────────────────────────────────────
# Достижения
# ─────────────────────────────────────────────────────────────

def check_achievements(client: Client) -> list[ClientAchievement]:
    """
    Проверяет активные достижения. Возвращает новые ClientAchievement.
    Типы правил: visits_count, spent_sum, year_together, referrals_count.
    """
    unlocked = []
    already = set(
        ClientAchievement.objects.filter(client=client)
        .values_list('definition_id', flat=True)
    )

    for defn in AchievementDefinition.objects.filter(is_active=True):
        if defn.pk in already:
            continue
        if not _achievement_matches(defn, client):
            continue
        obj, created = ClientAchievement.objects.get_or_create(
            client=client, definition=defn,
        )
        if created:
            unlocked.append(obj)
            logger.info(
                'achievement.unlock client=%s code=%s',
                client.pk, defn.code,
            )
    return unlocked


def _achievement_matches(defn: AchievementDefinition, client: Client) -> bool:
    rule = defn.rule_type
    params = defn.rule_params or {}

    if rule == 'visits_count':
        return client.total_bookings >= int(params.get('count', 0))
    if rule == 'spent_sum':
        return client.total_spent >= Decimal(str(params.get('sum', 0)))
    if rule == 'year_together':
        threshold = timezone.now() - timedelta(days=365)
        return client.first_visit is not None and client.first_visit <= threshold
    if rule == 'referrals_count':
        count = Referral.objects.filter(
            referrer=client, status=Referral.STATUS_REWARDED,
        ).count()
        return count >= int(params.get('count', 0))
    logger.warning('achievement.unknown_rule code=%s rule=%s', defn.code, rule)
    return False