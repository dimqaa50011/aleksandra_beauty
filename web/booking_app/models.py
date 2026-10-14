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
    """Мини-CRM: история клиентов по email для умной верификации"""
    email = models.EmailField('Email клиента', unique=True, db_index=True)
    is_verified = models.BooleanField('Email подтвержден', default=False)
    total_bookings = models.PositiveIntegerField('Всего записей', default=0)
    first_visit = models.DateTimeField('Первый визит', auto_now_add=True)
    last_visit = models.DateTimeField('Последний визит', auto_now=True)

    class Meta:
        verbose_name = 'Клиент (CRM)'
        verbose_name_plural = 'Клиенты (CRM)'

    def __str__(self):
        return self.email


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
        ('cancelled', '❌ Отменено'),
    ]

    client_name = models.CharField('Имя клиента', max_length=100)
    phone = models.CharField('Телефон', max_length=20)
    email = models.EmailField('Электронная почта', blank=True, null=True)
    
    # === ИЗМЕНЕНО: Теперь поддерживаем несколько услуг ===
    services = models.ManyToManyField(
        'beauty_app.Service', 
        verbose_name='Услуги',
        related_name='bookings'
    )
    
    appointment_datetime = models.DateTimeField('Дата и время записи')
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='confirmed')
    google_event_id = models.CharField('ID события в Google', max_length=255, blank=True, null=True, editable=False)
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Запись клиента'
        verbose_name_plural = 'Записи клиентов'
        ordering = ['-appointment_datetime']
        db_table = 'beauty_app_booking' # <-- ТРЮК: используем старую таблицу в БД

    def __str__(self):
        # === ИЗМЕНЕНО: Собираем названия всех услуг через запятую ===
        services_names = ", ".join([s.name for s in self.services.all()])
        return f"{self.client_name} — {services_names} ({self.appointment_datetime.strftime('%d.%m.%Y %H:%M')})"
    
    @property
    def total_duration(self):
        """Возвращает общую длительность всех услуг в записи"""
        return sum(s.duration for s in self.services.all() if s.duration)


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