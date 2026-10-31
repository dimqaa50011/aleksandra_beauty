import logging
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, AuthenticationFailed

from booking_app.models import Client, Booking
from booking_app.utils import (
    normalize_phone, phone_variants, find_client_by_phone,
)
from cert_app.models import CertificateModel

from ..models import (
    CabinetUser, ClientRefreshToken, PasswordResetCode, Referral,
)
from ..authentication import issue_access_token

logger = logging.getLogger(__name__)

PASSWORD_RESET_TTL_MINUTES = 15
PASSWORD_RESET_MAX_ATTEMPTS = 5

# Заглушка — заменить на реальный вызов твоего SMS-сервиса.
# Сигнатура: send_sms(phone: str, text: str) -> bool
def _send_sms(phone: str, text: str) -> bool:
    from django.conf import settings
    sender = getattr(settings, 'CABINET_SMS_SENDER', None)
    if sender is None:
        logger.warning('SMS-сервис не настроен. SMS для %s: %s', phone, text)
        return False
    return sender(phone, text)


# ─────────────────────────────────────────────────────────────
# Регистрация
# ─────────────────────────────────────────────────────────────

@transaction.atomic
def register(
    *,
    phone: str,
    password: str,
    name: str = '',
    email: str = '',
    consent_pd: bool,
    consent_marketing: bool = False,
    ref_code: str = '',
    ip: str | None = None,
    user_agent: str = '',
    platform: str = '',
) -> tuple[CabinetUser, str, str]:
    """Создаёт CabinetUser. Возвращает (user, access_token, refresh_raw)."""

    if not consent_pd:
        raise ValidationError({'consent_pd': 'Требуется согласие на обработку ПД'})

    normalized = normalize_phone(phone)
    if not normalized:
        raise ValidationError({'phone': 'Некорректный телефон'})

    if CabinetUser.objects.filter(phone=normalized).exists():
        raise ValidationError({'phone': 'Этот телефон уже зарегистрирован'})

    # Ищем существующего Client или создаём нового
    client = find_client_by_phone(phone)
    if client is None:
        client = Client.objects.create(
            phone=phone.strip(),
            name=name.strip()[:100],
            email=email.strip() or None,
        )
    else:
        # Дополняем пустые поля, но не перезаписываем заполненные
        changed = []
        if name and not client.name:
            client.name = name.strip()[:100]
            changed.append('name')
        if email and not client.email:
            client.email = email.strip()
            changed.append('email')
        if changed:
            client.save(update_fields=changed)

    # Реферал — только для новых клиентов по валидному коду
    referrer_user = None
    if ref_code:
        referrer_user = CabinetUser.objects.filter(
            referral_code=ref_code.strip().upper(), is_active=True,
        ).first()
        if referrer_user and referrer_user.client_id == client.pk:
            referrer_user = None  # сам себя не приглашаешь

    user = CabinetUser.objects.create_user(
        phone=normalized,
        password=password,
        client=client,
        consent_pd_at=timezone.now(),
        consent_marketing=consent_marketing,
        consent_marketing_at=timezone.now() if consent_marketing else None,
        last_login_ip=ip,
    )
    user.last_login = timezone.now()
    user.referral_code = user.generate_referral_code()
    user.save(update_fields=['last_login', 'referral_code'])

    # Линкуем «бесхозные» брони и сертификаты по телефону
    _link_orphans(client)

    # Создаём реферальную связь
    if referrer_user:
        Referral.objects.get_or_create(
            referrer=referrer_user.client,
            referee=client,
            defaults={'status': Referral.STATUS_REGISTERED},
        )
        # TODO: начисление малых бонусов обоим — вызывать после того,
        # как будет готов services/bonuses.py
        # accrue_bonuses(referrer_user.client, REFERRAL_REGISTER_BONUS, 'referral_registered', referral=ref)

    access = issue_access_token(user)
    _, refresh_raw = ClientRefreshToken.issue(
        user, user_agent=user_agent, platform=platform,
    )
    return user, access, refresh_raw


def _link_orphans(client: Client) -> None:
    """Привязывает Booking и сертификаты без client, совпадающие по телефону."""
    variants = phone_variants(client.phone)
    if not variants:
        return
    Booking.objects.filter(client__isnull=True, phone__in=variants).update(client=client)
    CertificateModel.objects.filter(client__isnull=True, phone__in=variants).update(client=client)


# ─────────────────────────────────────────────────────────────
# Вход
# ─────────────────────────────────────────────────────────────

def login(
    *,
    phone: str,
    password: str,
    ip: str | None = None,
    user_agent: str = '',
    platform: str = '',
) -> tuple[CabinetUser, str, str]:
    """Возвращает (user, access_token, refresh_raw) или бросает AuthenticationFailed."""

    normalized = normalize_phone(phone)
    if not normalized:
        raise AuthenticationFailed('Неверный телефон или пароль')

    user = CabinetUser.objects.select_related('client').filter(phone=normalized).first()
    if user is None or not user.check_password(password):
        raise AuthenticationFailed('Неверный телефон или пароль')
    if not user.is_active or user.is_blocked:
        raise AuthenticationFailed('Аккаунт заблокирован')

    user.last_login = timezone.now()
    user.last_login_ip = ip
    user.save(update_fields=['last_login', 'last_login_ip'])

    access = issue_access_token(user)
    _, refresh_raw = ClientRefreshToken.issue(
        user, user_agent=user_agent, platform=platform,
    )
    return user, access, refresh_raw


def logout(raw_refresh: str) -> None:
    tok = ClientRefreshToken.find_active(raw_refresh)
    if tok:
        tok.revoke()


def refresh(raw_refresh: str, *, user_agent: str = '', platform: str = ''):
    """Ротирует refresh. Возвращает (user, new_access, new_refresh_raw)."""
    tok = ClientRefreshToken.find_active(raw_refresh)
    if tok is None:
        raise AuthenticationFailed('Invalid refresh token')

    user = tok.user
    if not user.is_active or user.is_blocked:
        tok.revoke()
        raise AuthenticationFailed('Аккаунт заблокирован')

    tok.revoke()
    access = issue_access_token(user)
    _, new_raw = ClientRefreshToken.issue(
        user, user_agent=user_agent or tok.user_agent, platform=platform or tok.platform,
    )
    return user, access, new_raw


# ─────────────────────────────────────────────────────────────
# Сброс пароля через SMS
# ─────────────────────────────────────────────────────────────

def request_password_reset(phone: str, *, ip: str | None = None) -> None:
    """ВСЕГДА успех (не раскрываем, есть ли аккаунт). SMS шлём только если есть."""
    normalized = normalize_phone(phone)
    if not normalized:
        return

    user = CabinetUser.objects.filter(phone=normalized, is_active=True).first()
    if user is None:
        return

    # Cooldown: не чаще 1 раза в 60 секунд
    last = user.password_reset_codes.first()
    if last and (timezone.now() - last.created_at).total_seconds() < 60:
        return

    code = f'{secrets.randbelow(1_000_000):06d}'
    PasswordResetCode.objects.create(
        user=user,
        code=code,
        expires_at=timezone.now() + timedelta(minutes=PASSWORD_RESET_TTL_MINUTES),
        ip_address=ip,
    )
    _send_sms(user.client.phone, f'Код для сброса пароля: {code}. Действует {PASSWORD_RESET_TTL_MINUTES} мин.')


def confirm_password_reset(phone: str, code: str, new_password: str) -> CabinetUser:
    normalized = normalize_phone(phone)
    user = CabinetUser.objects.filter(phone=normalized, is_active=True).first()
    if user is None:
        raise ValidationError({'code': 'Неверный код'})

    reset = user.password_reset_codes.filter(is_used=False).first()
    if reset is None or reset.is_expired():
        raise ValidationError({'code': 'Код истёк или не запрашивался'})

    if reset.attempts >= PASSWORD_RESET_MAX_ATTEMPTS:
        raise ValidationError({'code': 'Слишком много попыток. Запросите новый код'})

    if reset.code != code.strip():
        reset.attempts += 1
        reset.save(update_fields=['attempts'])
        raise ValidationError({'code': 'Неверный код'})

    reset.is_used = True
    reset.save(update_fields=['is_used'])

    user.set_password(new_password)
    user.save(update_fields=['password'])
    # Отзываем все сессии
    user.refresh_tokens.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())
    return user