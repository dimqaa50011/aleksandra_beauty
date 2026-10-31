import random
from django.db import models
from django.utils import timezone
from datetime import timedelta
import secrets

class APIToken(models.Model):
    """Токены для доступа к API"""
    name = models.CharField('Название', max_length=100, help_text="Например: VK Mini App")
    token = models.CharField('Токен', max_length=255, unique=True, db_index=True)
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    last_used = models.DateTimeField('Последнее использование', null=True, blank=True)
    
    class Meta:
        verbose_name = 'API токен'
        verbose_name_plural = 'API токены'
    
    def __str__(self):
        return f"{self.name} ({self.token[:8]}...)"
    
    @classmethod
    def generate_token(cls, name):
        """Генерирует новый токен"""
        token = secrets.token_urlsafe(64)
        return cls.objects.create(name=name, token=token)


class Client(models.Model):
    """Профиль клиента (CRM)"""
    # Телефон - главный идентификатор
    phone = models.CharField('Телефон', max_length=20, unique=True, db_index=True)
    name = models.CharField('Имя', max_length=100, blank=True)
    # Почта необязательна (так как на сайте она опциональна)
    email = models.EmailField('Email', blank=True, null=True, db_index=True) 
    
    # Статистика (заполняется при завершении приемов)
    total_bookings = models.PositiveIntegerField('Всего визитов', default=0)
    total_spent = models.DecimalField('Всего потрачено', max_digits=10, decimal_places=2, default=0)
    first_visit = models.DateTimeField('Первый визит', auto_now_add=True)
    last_visit = models.DateTimeField('Последний визит', auto_now=True)
    
    # Заметки администратора (аллергии, предпочтения)
    notes = models.TextField('Заметки', blank=True)
    
    bonus_balance = models.IntegerField('Баланс бонусов', default=0)

    class Meta:
        verbose_name = 'Клиент (CRM)'
        verbose_name_plural = 'Клиенты (CRM)'
        ordering = ['-last_visit']

    def __str__(self):
        return f"{self.name} ({self.phone})" if self.name else self.phone


class EmailVerificationCode(models.Model):
    """Коды подтверждения email"""
    email = models.EmailField('Email')
    code = models.CharField('Код', max_length=6)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    is_used = models.BooleanField('Использован', default=False)
    attempts = models.IntegerField('Попыток ввода', default=0)

    class Meta:
        verbose_name = 'Код подтверждения'
        verbose_name_plural = 'Коды подтверждения'
        ordering = ['-created_at']

    @property
    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    @classmethod
    def generate_code(cls, email):
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        return cls.objects.create(email=email, code=code)


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', '⏳ Ожидает подтверждения'),
        ('confirmed', '✅ Подтверждено'),
        ('completed', '🎉 Выполнено (Прием прошел)'), # НОВЫЙ СТАТУС
        ('no_show', '👻 Не пришел'),                 # НОВЫЙ СТАТУС
        ('cancelled', '❌ Отменено'),
    ]

    # СВЯЗЬ С КЛИЕНТОМ
    client = models.ForeignKey(
        Client, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='bookings',
        verbose_name='Клиент'
    )

    client_name = models.CharField('Имя (в записи)', max_length=100)
    phone = models.CharField('Телефон (в записи)', max_length=20)
    email = models.EmailField('Email (в записи)', blank=True, null=True)
    
    services = models.ManyToManyField('beauty_app.Service', verbose_name='Услуги', related_name='bookings')
    appointment_datetime = models.DateTimeField('Дата и время записи')
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    google_event_id = models.CharField('ID события в Google', max_length=255, blank=True, null=True, editable=False)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    # Флаги напоминаний
    reminded_24h = models.BooleanField('Напоминание 24ч отправлено', default=False)
    reminded_2h = models.BooleanField('Напоминание 2ч отправлено', default=False)
    reminded_15m = models.BooleanField('Напоминание 15м отправлено', default=False)
    review_token = models.UUIDField(null=True, blank=True, unique=True, db_index=True)
    is_read = models.BooleanField('Прочитано админом', default=False)
    
    use_bonuses_requested = models.BooleanField('Запрошено списание бонусов', default=False)
    bonuses_to_apply = models.PositiveIntegerField('Сколько бонусов применить', default=0)
    bonuses_applied = models.PositiveIntegerField('Списано бонусов', default=0)
    cashback_accrued = models.PositiveIntegerField('Начислено кэшбэка', default=0)

    # ─── Отмена (заполняется из cabinet_app или админки) ───
    cancel_reason = models.CharField('Причина отмены (код)', max_length=50, blank=True)
    cancel_reason_text = models.CharField('Причина отмены (текст)', max_length=255, blank=True)
    cancelled_by = models.CharField(
        'Кто отменил', max_length=20, blank=True,
        help_text='client / admin',
    )
    cancelled_at = models.DateTimeField('Отменено', null=True, blank=True)

    # ─── Перенос ───
    rescheduled_from = models.DateTimeField('Перенесено с', null=True, blank=True)
    bonuses_processed_at = models.DateTimeField(
        'Бонусы обработаны', null=True, blank=True,
        help_text='Идемпотентность apply_bonus_effects',
    )

    class Meta:
        verbose_name = 'Запись клиента'
        verbose_name_plural = 'Записи клиентов'
        ordering = ['-appointment_datetime']

    def __str__(self):
        return f"{self.client_name} — {self.appointment_datetime.strftime('%d.%m.%Y %H:%M')}"

    @property
    def total_duration(self):
        return sum(s.duration for s in self.services.all() if s.duration)
        
    @property
    def total_price(self):
        return sum(s.price for s in self.services.all() if s.price)

class DayOff(models.Model):
    """Даты, когда студия не работает"""
    date = models.DateField('Дата выходного', unique=True, help_text="Например: 2026-10-15")
    reason = models.CharField('Причина (необязательно)', max_length=100, blank=True)
    created_at = models.DateTimeField('Добавлено', auto_now_add=True)

    class Meta:
        verbose_name = 'Выходной день'
        verbose_name_plural = 'Выходные дни'
        ordering = ['-date']
        db_table = 'beauty_app_dayoff' # <-- ТРЮК

    def __str__(self):
        reason_str = f" ({self.reason})" if self.reason else ""
        return f"{self.date.strftime('%d.%m.%Y')}{reason_str}"


class BlockedSlot(models.Model):
    """Заблокированные временные слоты (выходные, личные дела, перерывы)"""
    
    TYPE_CHOICES = [
        ('day_off', 'Выходной день'),
        ('personal', 'Личные дела'),
        ('maintenance', 'Технический перерыв'),
        ('other', 'Другое'),
    ]
    
    date = models.DateField('Дата')
    is_full_day = models.BooleanField('На весь день', default=False)
    start_time = models.TimeField('Начало', blank=True, null=True)
    end_time = models.TimeField('Конец', blank=True, null=True)
    reason = models.CharField('Причина', max_length=100, blank=True)
    slot_type = models.CharField('Тип', max_length=20, choices=TYPE_CHOICES, default='day_off')
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Заблокированный слот'
        verbose_name_plural = 'Заблокированные слоты'
        ordering = ['date', 'start_time']
        db_table = 'beauty_app_blockedslot'

    def __str__(self):
        if self.is_full_day:
            return f"{self.date.strftime('%d.%m.%Y')} - Весь день ({self.get_slot_type_display()})"
        return f"{self.date.strftime('%d.%m.%Y')} {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')} ({self.get_slot_type_display()})"


class PushSubscription(models.Model):
    """Подписки на пуш-уведомления для админов"""
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.URLField(max_length=500)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Подписка на пуши'
        verbose_name_plural = 'Подписки на пуши'
        unique_together = ('user', 'endpoint')

    def __str__(self):
        return f"Push для {self.user.username}: {self.endpoint[:50]}..."
    


class DeviceFCMToken(models.Model):
    """FCM-токены мобильных устройств админов"""
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='fcm_tokens')
    token = models.CharField(max_length=500, unique=True)
    platform = models.CharField(max_length=20, blank=True)  # 'android' / 'ios'
    device_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'FCM токен устройства'
        verbose_name_plural = 'FCM токены устройств'
        ordering = ['-last_used']

    def __str__(self):
        return f"{self.user.username}: {self.token[:40]}..."


class SMSTemplate(models.Model):
    """Шаблоны SMS-сообщений"""
    key = models.CharField(
        max_length=50, 
        unique=True, 
        help_text="Уникальный код: creation, edit, cancel, reminder_24h, reminder_2h, reminder_15m"
    )
    description = models.CharField(max_length=150, blank=True, help_text="Описание для админа")
    text = models.TextField(
        help_text="Доступные переменные: {name}, {date}, {time}, {address}"
    )

    class Meta:
        verbose_name = 'Шаблон SMS'
        verbose_name_plural = 'Шаблоны SMS'

    def __str__(self):
        return f"{self.description or self.key}"