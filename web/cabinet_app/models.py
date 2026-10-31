import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager


class CabinetUserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('Телефон обязателен')
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class CabinetUser(AbstractBaseUser):
    """Аккаунт клиента в личном кабинете (PWA)."""

    client = models.OneToOneField(
        'booking_app.Client',
        on_delete=models.CASCADE,
        related_name='cabinet_user',
        verbose_name='Клиент (CRM)',
    )
    # Денормализация: нормализованный телефон для USERNAME_FIELD.
    # Источник истины — Client.phone_normalized, синхронизируется при сохранении.
    phone = models.CharField('Телефон (нормализованный)', max_length=12, unique=True, db_index=True)
    
        # Внутри класса CabinetUser
    avatar = models.ImageField('Аватар', upload_to='avatars/', null=True, blank=True)

    is_active = models.BooleanField('Активен', default=True)
    is_blocked = models.BooleanField('Заблокирован админом', default=False)
    block_reason = models.CharField('Причина блокировки', max_length=255, blank=True)

    consent_pd_at = models.DateTimeField('Согласие на обработку ПД', null=True, blank=True)
    consent_marketing = models.BooleanField('Согласие на маркетинг', default=False)
    consent_marketing_at = models.DateTimeField('Дата согласия на маркетинг', null=True, blank=True)

    referral_code = models.CharField('Реферальный код', max_length=12, unique=True, db_index=True, blank=True)

    last_login_ip = models.GenericIPAddressField('IP последнего входа', null=True, blank=True)

    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)

    objects = CabinetUserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []  # для createsuperuser-подобных сценариев; нам не нужны

    class Meta:
        verbose_name = 'Аккаунт кабинета'
        verbose_name_plural = 'Аккаунты кабинета'

    def __str__(self):
        return f'{self.client} (кабинет)'

    def generate_referral_code(self) -> str:
        alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        for _ in range(10):
            code = ''.join(secrets.choice(alphabet) for _ in range(8))
            if not CabinetUser.objects.filter(referral_code=code).exists():
                return code
        raise RuntimeError('Не удалось сгенерировать реф-код')


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────
# Токены и сброс пароля
# ─────────────────────────────────────────────────────────────

class ClientRefreshToken(models.Model):
    """Opaque refresh-токен. В БД — только sha256."""
    user = models.ForeignKey(CabinetUser, on_delete=models.CASCADE, related_name='refresh_tokens')
    token_hash = models.CharField('Хэш токена', max_length=64, unique=True, db_index=True)
    user_agent = models.CharField('User-Agent', max_length=255, blank=True)
    platform = models.CharField('Платформа', max_length=20, blank=True)  # ios / android / desktop
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    last_used_at = models.DateTimeField('Последнее использование', null=True, blank=True)
    expires_at = models.DateTimeField('Истекает')
    revoked_at = models.DateTimeField('Отозван', null=True, blank=True)

    class Meta:
        verbose_name = 'Refresh-токен кабинета'
        verbose_name_plural = 'Refresh-токены кабинета'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'revoked_at']),
        ]

    def revoke(self):
        self.revoked_at = timezone.now()
        self.save(update_fields=['revoked_at'])

    @classmethod
    def issue(cls, user: CabinetUser, *, ttl_days: int = 90,
              user_agent: str = '', platform: str = '') -> tuple['ClientRefreshToken', str]:
        raw = secrets.token_urlsafe(48)
        obj = cls.objects.create(
            user=user,
            token_hash=_hash_token(raw),
            user_agent=user_agent[:255],
            platform=platform[:20],
            expires_at=timezone.now() + timedelta(days=ttl_days),
        )
        return obj, raw

    @classmethod
    def find_active(cls, raw: str) -> 'ClientRefreshToken | None':
        return cls.objects.filter(
            token_hash=_hash_token(raw),
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).select_related('user__client').first()


class PasswordResetCode(models.Model):
    """Одноразовый код сброса пароля через SMS."""
    user = models.ForeignKey(CabinetUser, on_delete=models.CASCADE, related_name='password_reset_codes')
    code = models.CharField('Код', max_length=6)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    expires_at = models.DateTimeField('Истекает')
    is_used = models.BooleanField('Использован', default=False)
    attempts = models.PositiveSmallIntegerField('Попыток ввода', default=0)
    ip_address = models.GenericIPAddressField('IP', null=True, blank=True)

    class Meta:
        verbose_name = 'Код сброса пароля'
        verbose_name_plural = 'Коды сброса пароля'
        ordering = ['-created_at']

    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at


# ─────────────────────────────────────────────────────────────
# Push
# ─────────────────────────────────────────────────────────────

class ClientPushSubscription(models.Model):
    """Web Push подписка клиента (PWA)."""
    user = models.ForeignKey(CabinetUser, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.URLField('Endpoint', max_length=500)
    p256dh = models.CharField('p256dh', max_length=200)
    auth = models.CharField('auth', max_length=100)
    platform = models.CharField('Платформа', max_length=20, blank=True)  # ios / android / desktop
    is_standalone = models.BooleanField('Standalone (iOS)', default=False)
    user_agent = models.CharField('User-Agent', max_length=255, blank=True)
    is_active = models.BooleanField('Активна', default=True)
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    last_seen_at = models.DateTimeField('Активность', auto_now=True)

    class Meta:
        verbose_name = 'Push-подписка клиента'
        verbose_name_plural = 'Push-подписки клиентов'
        ordering = ['-last_seen_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'endpoint'], name='uniq_cabinetuser_endpoint'),
        ]

    def __str__(self):
        return f'{self.user_id}: {self.endpoint[:40]}…'


# ─────────────────────────────────────────────────────────────
# Лог уведомлений
# ─────────────────────────────────────────────────────────────

class NotificationLog(models.Model):
    """Лог доставки уведомлений: идемпотентность + диагностика."""
    CHANNEL_SMS = 'sms'
    CHANNEL_PUSH = 'push'
    CHANNEL_TELEGRAM = 'telegram'
    CHANNEL_CHOICES = [
        (CHANNEL_SMS, 'SMS'),
        (CHANNEL_PUSH, 'Push'),
        (CHANNEL_TELEGRAM, 'Telegram'),
    ]
    STATUS_PENDING = 'pending'
    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'
    STATUS_SKIPPED = 'skipped'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Ожидает'),
        (STATUS_SENT, 'Отправлено'),
        (STATUS_FAILED, 'Ошибка'),
        (STATUS_SKIPPED, 'Пропущено'),
    ]

    client = models.ForeignKey(
        'booking_app.Client', on_delete=models.CASCADE, related_name='cabinet_notifications',
    )
    booking = models.ForeignKey(
        'booking_app.Booking', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cabinet_notifications',
    )
    event_type = models.CharField('Событие', max_length=50, db_index=True)
    channel = models.CharField('Канал', max_length=20, choices=CHANNEL_CHOICES)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    subscription = models.ForeignKey(
        ClientPushSubscription, on_delete=models.SET_NULL, null=True, blank=True,
    )
    payload = models.JSONField('Payload', default=dict, blank=True)
    error = models.TextField('Ошибка', blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    sent_at = models.DateTimeField('Отправлено', null=True, blank=True)

    class Meta:
        verbose_name = 'Лог уведомления'
        verbose_name_plural = 'Лог уведомлений'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['booking', 'event_type', 'channel', 'status']),
            models.Index(fields=['client', '-created_at']),
        ]




# ─────────────────────────────────────────────────────────────
# Бонусы
# ─────────────────────────────────────────────────────────────

class BonusTransaction(models.Model):
    """История начислений и списаний бонусов."""
    TYPE_ACCRUAL = 'accrual'
    TYPE_SPEND = 'spend'
    TYPE_EXPIRE = 'expire'
    TYPE_ADJUST = 'adjust'
    TYPE_CHOICES = [
        (TYPE_ACCRUAL, 'Начисление'),
        (TYPE_SPEND, 'Списание'),
        (TYPE_EXPIRE, 'Сгорание'),
        (TYPE_ADJUST, 'Корректировка'),
    ]

    client = models.ForeignKey(
        'booking_app.Client', on_delete=models.CASCADE, related_name='bonus_transactions',
    )
    amount = models.IntegerField('Сумма (со знаком)')
    type = models.CharField('Тип', max_length=20, choices=TYPE_CHOICES)
    reason = models.CharField('Причина (код)', max_length=100)
    description = models.CharField('Описание', max_length=255, blank=True)

    booking = models.ForeignKey(
        'booking_app.Booking', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bonus_transactions',
    )
    referral = models.ForeignKey(
        'Referral', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bonus_transactions',
    )

    balance_after = models.IntegerField('Баланс после операции')
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_bonus_transactions',
    )

    class Meta:
        verbose_name = 'Транзакция бонусов'
        verbose_name_plural = 'Транзакции бонусов'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', '-created_at']),
            models.Index(fields=['reason']),
        ]


class CashbackRule(models.Model):
    """Правило кэшбэка на услугу в определённый период."""
    service = models.ForeignKey(
        'beauty_app.Service', on_delete=models.CASCADE, related_name='cashback_rules',
    )
    percent = models.DecimalField(
        'Процент кэшбэка', max_digits=5, decimal_places=2,
        help_text='Например, 10.00 = 10% от стоимости услуги',
    )
    valid_from = models.DateField('Действует с')
    valid_until = models.DateField('Действует по')
    is_active = models.BooleanField('Активно', default=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Правило кэшбэка'
        verbose_name_plural = 'Правила кэшбэка'
        ordering = ['-valid_from', 'service']
        indexes = [
            models.Index(fields=['service', 'valid_from', 'valid_until', 'is_active']),
        ]

    def __str__(self):
        return f'{self.service} — {self.percent}% ({self.valid_from}–{self.valid_until})'


# ─────────────────────────────────────────────────────────────
# Рефералка
# ─────────────────────────────────────────────────────────────

class Referral(models.Model):
    """Связь «пригласил → пришёл»."""
    STATUS_REGISTERED = 'registered'
    STATUS_FIRST_VISIT = 'first_visit_done'
    STATUS_REWARDED = 'rewarded'
    STATUS_CHOICES = [
        (STATUS_REGISTERED, 'Зарегистрирован'),
        (STATUS_FIRST_VISIT, 'Первый визит состоялся'),
        (STATUS_REWARDED, 'Награждены'),
    ]

    referrer = models.ForeignKey(
        'booking_app.Client', on_delete=models.CASCADE, related_name='referrals_made',
    )
    referee = models.ForeignKey(
        'booking_app.Client', on_delete=models.CASCADE, related_name='referral_source',
    )
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default=STATUS_REGISTERED)

    registered_at = models.DateTimeField('Регистрация', auto_now_add=True)
    first_visit_at = models.DateTimeField('Первый визит', null=True, blank=True)
    rewarded_at = models.DateTimeField('Награждены', null=True, blank=True)

    class Meta:
        verbose_name = 'Реферал'
        verbose_name_plural = 'Рефералы'
        ordering = ['-registered_at']
        constraints = [
            models.UniqueConstraint(fields=['referrer', 'referee'], name='uniq_referral_pair'),
        ]

    def __str__(self):
        return f'{self.referrer} → {self.referee} ({self.get_status_display()})'


# ─────────────────────────────────────────────────────────────
# Достижения
# ─────────────────────────────────────────────────────────────

class AchievementDefinition(models.Model):
    """Определение достижения (настраивается из админки)."""
    code = models.CharField('Код', max_length=50, unique=True)
    title = models.CharField('Название', max_length=100)
    description = models.CharField('Описание', max_length=255)
    icon = models.CharField('Иконка', max_length=50, blank=True, help_text='Emoji или имя иконки')
    rule_type = models.CharField(
        'Тип правила', max_length=50,
        help_text='visits_count / spent_sum / year_together / reviews_count / referrals_count',
    )
    rule_params = models.JSONField('Параметры правила', default=dict, blank=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)
    is_active = models.BooleanField('Активно', default=True)

    class Meta:
        verbose_name = 'Достижение (определение)'
        verbose_name_plural = 'Достижения (определения)'
        ordering = ['sort_order', 'code']

    def __str__(self):
        return f'{self.title} [{self.code}]'


class ClientAchievement(models.Model):
    """Разблокированное клиентом достижение."""
    client = models.ForeignKey(
        'booking_app.Client', on_delete=models.CASCADE, related_name='achievements',
    )
    definition = models.ForeignKey(
        AchievementDefinition, on_delete=models.CASCADE, related_name='unlocks',
    )
    unlocked_at = models.DateTimeField('Разблокировано', auto_now_add=True)
    seen_by_client = models.BooleanField('Увидено клиентом', default=False)

    class Meta:
        verbose_name = 'Достижение клиента'
        verbose_name_plural = 'Достижения клиентов'
        ordering = ['-unlocked_at']
        constraints = [
            models.UniqueConstraint(fields=['client', 'definition'], name='uniq_client_achievement'),
        ]


# ─────────────────────────────────────────────────────────────
# Персональные предложения
# ─────────────────────────────────────────────────────────────

class PersonalOffer(models.Model):
    """Персональное предложение клиенту (назначается из админки)."""
    CTA_NONE = 'none'
    CTA_BOOK = 'book'
    CTA_URL = 'url'
    CTA_CHOICES = [
        (CTA_NONE, 'Без действия'),
        (CTA_BOOK, 'Записаться на услугу'),
        (CTA_URL, 'Открыть ссылку'),
    ]

    client = models.ForeignKey(
        'booking_app.Client', on_delete=models.CASCADE, related_name='personal_offers',
    )
    title = models.CharField('Заголовок', max_length=100)
    body = models.TextField('Текст')
    image = models.ImageField('Картинка', upload_to='offers/', null=True, blank=True)

    cta_type = models.CharField('Тип CTA', max_length=20, choices=CTA_CHOICES, default=CTA_NONE)
    cta_payload = models.CharField('Payload CTA', max_length=255, blank=True,
                                    help_text='service_id для book или URL')

    valid_until = models.DateTimeField('Действует до', null=True, blank=True)
    is_active = models.BooleanField('Активно', default=True)

    seen_at = models.DateTimeField('Просмотрено', null=True, blank=True)
    used_at = models.DateTimeField('Использовано', null=True, blank=True)

    created_at = models.DateTimeField('Создано', auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_personal_offers',
    )

    class Meta:
        verbose_name = 'Персональное предложение'
        verbose_name_plural = 'Персональные предложения'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', 'is_active']),
        ]