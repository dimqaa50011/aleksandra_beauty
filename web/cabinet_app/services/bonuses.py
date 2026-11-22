import logging
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from booking_app.models import Bonus, BonusBalance, Client, Booking
from cert_app.models import CertificateModel

from ..models import (
    AchievementDefinition,
    CashbackRule,
    ClientAchievement,
    LoyaltySettings,
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
    custom_ttl_days: int | None = None,
) -> Bonus | None:
    if amount <= 0:
        return None

    wallet, _ = BonusBalance.objects.get_or_create(client=client)
    
    if custom_ttl_days is not None:
        ttl_days = custom_ttl_days
        logger.info(f'Использован кастомный TTL: {ttl_days} дней для причины {reason}')
    else:
        defaults = {'cashback': 180, 'referral': 365, 'welcome': 30}
        ttl_days = defaults.get(reason, 180)
    
    expires_at = timezone.now() + timedelta(days=ttl_days)
    
    bonus = Bonus.objects.create(
        wallet=wallet,
        amount=amount,
        reason=reason,
        expires_at=expires_at,
        booking=booking
    )
    return bonus


@transaction.atomic
def spend_bonuses(
    client: Client, amount: int, reason: str, *, booking: Booking | None = None, referral: Referral | None = None, description: str = '', created_by=None
) -> int:
    if amount <= 0:
        return 0

    wallet, _ = BonusBalance.objects.get_or_create(client=client)
    available = wallet.get_total()
    actual_to_spend = min(amount, available)
    
    if actual_to_spend <= 0:
        return 0

    remaining_to_spend = actual_to_spend
    active_bonuses = wallet.bonuses.filter(
        is_spent=False, is_expired=False, expires_at__gt=timezone.now()
    ).order_by('expires_at')
    
    for bonus in active_bonuses:
        if remaining_to_spend <= 0:
            break
        if bonus.amount <= remaining_to_spend:
            remaining_to_spend -= bonus.amount
            bonus.is_spent = True
            bonus.amount = 0
            bonus.save(update_fields=['is_spent', 'amount'])
        else:
            bonus.amount -= remaining_to_spend
            remaining_to_spend = 0
            bonus.save(update_fields=['amount'])

    return actual_to_spend


def get_bonus_balance(client: Client) -> int:
    return client.bonus_wallet.get_total()


def grant_welcome_bonus(client: Client) -> None:
    config = LoyaltySettings.load()
    if config.welcome_bonus_amount > 0:
        accrue_bonuses(
            client=client,
            amount=config.welcome_bonus_amount,
            reason='welcome',
            description='Приветственные бонусы за регистрацию',
            custom_ttl_days=config.welcome_bonus_ttl_days
        )


# ─────────────────────────────────────────────────────────────
# Лимит и кэшбэк
# ─────────────────────────────────────────────────────────────

def certificate_coverage(booking: Booking) -> Decimal:
    cert = booking.reserved_certificates.filter(is_used=False, reserved_for_booking=booking).first()
    if cert is None:
        cert = booking.used_certificates.first()
    if cert is None:
        return Decimal('0')
    cert_amount = Decimal(str(cert.price))
    return min(cert_amount, booking.total_price)


def max_bonuses_for_booking(booking: Booking) -> int:
    total = booking.total_price
    covered = certificate_coverage(booking)
    base = total - covered
    if base <= 0:
        return 0
    
    config = LoyaltySettings.load()
    percent = Decimal(str(config.max_bonus_spend_percent))
    return int(base * percent / Decimal('100'))


def calculate_cashback(booking: Booking, bonuses_spent: int = 0, cert_covered: Decimal = Decimal('0')) -> int:
    visit_date = booking.appointment_datetime.date()
    services = list(booking.services.all())
    total_price = Decimal(str(booking.total_price))
    
    if total_price <= 0 or not services:
        return 0

    service_data = []
    for service in services:
        rule = CashbackRule.objects.filter(
            service=service, is_active=True,
            valid_from__lte=visit_date, valid_until__gte=visit_date,
        ).order_by('-valid_from').first()

        if rule:
            percent = rule.percent
        elif hasattr(service, 'cashback_percent') and service.cashback_percent is not None:
            percent = Decimal(str(service.cashback_percent))
        else:
            percent = Decimal('0')

        service_data.append({
            'price': Decimal(str(service.price)),
            'percent': percent,
            'cash_paid': Decimal(str(service.price))
        })

    if cert_covered > 0:
        cert_ratio = cert_covered / total_price
        for s in service_data:
            s['cash_paid'] -= (s['price'] * cert_ratio)

    service_data.sort(key=lambda x: x['percent'])
    remaining_bonuses = Decimal(str(bonuses_spent))

    for s in service_data:
        if remaining_bonuses <= 0:
            break
        deduction = min(s['cash_paid'], remaining_bonuses)
        s['cash_paid'] -= deduction
        remaining_bonuses -= deduction

    total_cashback = 0
    for s in service_data:
        if s['percent'] > 0 and s['cash_paid'] > 0:
            amount = int(s['cash_paid'] * s['percent'] / Decimal('100'))
            total_cashback += amount

    return total_cashback


# ─────────────────────────────────────────────────────────────
# Сертификаты
# ─────────────────────────────────────────────────────────────

@transaction.atomic
def reserve_certificate(cert: CertificateModel, booking: Booking) -> None:
    if cert.is_used:
        raise ValidationError('Сертификат уже использован')
    if cert.is_expired:
        raise ValidationError('Срок сертификата истёк')
    if cert.reserved_for_booking_id and cert.reserved_for_booking_id != booking.pk:
        raise ValidationError('Сертификат уже зарезервирован под другую запись')

    cert.reserved_for_booking = booking
    cert.save(update_fields=['reserved_for_booking'])


@transaction.atomic
def release_certificate(cert: CertificateModel) -> None:
    if cert.is_used:
        return
    cert.reserved_for_booking = None
    cert.save(update_fields=['reserved_for_booking'])


@transaction.atomic
def redeem_certificate_for_booking(cert_id: int, booking_id: int) -> CertificateModel:
    cert = CertificateModel.objects.select_for_update().filter(pk=cert_id, is_used=False).first()
    if not cert:
        raise ValidationError('Сертификат не найден или уже погашен')
    if cert.is_expired:
        raise ValidationError('Срок действия сертификата истек')

    booking = Booking.objects.get(pk=booking_id)

    cert.is_used = True
    cert.used_date = timezone.now()
    cert.used_booking = booking
    cert.reserved_for_booking = None
    cert.save(update_fields=['is_used', 'used_date', 'used_booking', 'reserved_for_booking'])
    return cert


# ─────────────────────────────────────────────────────────────
# Завершение визита
# ─────────────────────────────────────────────────────────────

@transaction.atomic
def apply_bonus_effects(booking: Booking, *, use_bonuses: bool = False, created_by=None) -> dict:
    booking = Booking.objects.select_for_update().get(pk=booking.pk)

    if booking.bonuses_processed_at is not None or booking.status != 'completed':
        return {}

    if booking.client_id is None:
        booking.bonuses_processed_at = timezone.now()
        booking.save(update_fields=['bonuses_processed_at'])
        return {}

    client = booking.client
    result = {'bonuses_spent': 0, 'cashback': 0, 'achievements_unlocked': []}

    # 1. СПИСАНИЕ БОНУСОВ
    bonuses_spent = 0
    if use_bonuses:
        max_allowed = max_bonuses_for_booking(booking)
        # ИСПРАВЛЕНО: Берем баланс из кошелька
        current_balance = client.bonus_wallet.get_total()
        to_spend = min(current_balance, max_allowed)

        if to_spend > 0:
            # ИСПРАВЛЕНО: spend_bonuses возвращает int, а не объект tx
            applied = spend_bonuses(
                client, to_spend, reason='visit', booking=booking,
                description=f'Оплата бонусами за визит #{booking.pk}', created_by=created_by,
            )
            booking.bonuses_applied = applied
            bonuses_spent = applied
            result['bonuses_spent'] = applied

    # 2. НАЧИСЛЕНИЕ КЭШБЭКА (умное)
    cert_covered = certificate_coverage(booking)
    # ИСПРАВЛЕНО: Передаем bonuses_spent и cert_covered в функцию
    cashback = calculate_cashback(booking, bonuses_spent=bonuses_spent, cert_covered=cert_covered)
    
    if cashback > 0:
        accrue_bonuses(
            client, cashback, reason='cashback', booking=booking,
            description=f'Кэшбэк за визит #{booking.pk}', created_by=created_by,
        )
        booking.cashback_accrued = cashback
        result['cashback'] = cashback

    # 3. Рефералка
    _process_referral_first_visit(client, booking, created_by=created_by)

    # 4. Достижения
    unlocked = check_achievements(client)
    result['achievements_unlocked'] = [a.definition.code for a in unlocked]

    # 5. Метка идемпотентности
    booking.bonuses_processed_at = timezone.now()
    booking.save(update_fields=['bonuses_processed_at', 'bonuses_applied', 'cashback_accrued'])

    # 6. Уведомление
    if result['cashback'] > 0:
        transaction.on_commit(lambda: _notify_cashback_safe(client.pk, booking.pk, result['cashback']))

    return result


@transaction.atomic
def handle_booking_cancelled(booking: Booking) -> None:
    if booking.bonuses_processed_at is not None:
        return
    cert = booking.reserved_certificates.filter(is_used=False).first()
    if cert is not None:
        release_certificate(cert)


def _notify_cashback_safe(client_pk: int, booking_pk: int, cashback: int) -> None:
    try:
        NotificationLog.objects.create(
            client_id=client_pk, booking_id=booking_pk, event_type='cashback_accrued',
            channel=NotificationLog.CHANNEL_PUSH, status=NotificationLog.STATUS_PENDING,
            payload={'title': 'Бонусы начислены', 'body': f'Вам начислено {cashback} бонусов за визит', 'url': '/bonuses'},
        )
    except Exception:
        logger.exception('notify.cashback failed')


# ─────────────────────────────────────────────────────────────
# Рефералка
# ─────────────────────────────────────────────────────────────

def process_referral_registration(referral: Referral, *, created_by=None) -> None:
    if referral.status != Referral.STATUS_REGISTERED or referral.referrer_id == referral.referee_id:
        return

    config = LoyaltySettings.load()
    ref_bonus = config.referral_register_referrer
    friend_bonus = config.referral_register_referee

    if ref_bonus > 0:
        accrue_bonuses(referral.referrer, ref_bonus, reason='referral_registered', referral=referral, created_by=created_by)
    if friend_bonus > 0:
        accrue_bonuses(referral.referee, friend_bonus, reason='referral_registered', referral=referral, created_by=created_by)


def _process_referral_first_visit(client: Client, booking: Booking, *, created_by=None) -> None:
    referral = Referral.objects.select_for_update().filter(referee=client, status=Referral.STATUS_REGISTERED).first()
    if referral is None or referral.referrer_id == referral.referee_id:
        return

    referral.status = Referral.STATUS_FIRST_VISIT
    referral.first_visit_at = timezone.now()
    referral.save(update_fields=['status', 'first_visit_at'])

    config = LoyaltySettings.load()
    ref_bonus = config.referral_first_visit_referrer
    friend_bonus = config.referral_first_visit_referee

    if ref_bonus > 0:
        accrue_bonuses(referral.referrer, ref_bonus, reason='referral_first_visit', referral=referral, created_by=created_by)
    if friend_bonus > 0:
        accrue_bonuses(referral.referee, friend_bonus, reason='referral_first_visit', referral=referral, created_by=created_by)

    referral.status = Referral.STATUS_REWARDED
    referral.rewarded_at = timezone.now()
    referral.save(update_fields=['status', 'rewarded_at'])


# ─────────────────────────────────────────────────────────────
# Достижения
# ─────────────────────────────────────────────────────────────

def check_achievements(client: Client) -> list[ClientAchievement]:
    unlocked = []
    already = set(ClientAchievement.objects.filter(client=client).values_list('definition_id', flat=True))

    for defn in AchievementDefinition.objects.filter(is_active=True):
        if defn.pk in already:
            continue
        if not _achievement_matches(defn, client):
            continue
        obj, created = ClientAchievement.objects.get_or_create(client=client, definition=defn)
        if created:
            unlocked.append(obj)
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
        count = Referral.objects.filter(referrer=client, status=Referral.STATUS_REWARDED).count()
        return count >= int(params.get('count', 0))
    return False