from django.db import models

class NotificationType(models.Model):
    code = models.CharField(
        'Код', max_length=50, unique=True, 
        help_text="Системный код для вызова из кода (например: reminder_24h, promo)"
    )
    name = models.CharField('Название для админа', max_length=100)
    description = models.CharField('Описание для клиента', max_length=255, blank=True)
    
    # Группа для красивого отображения на фронтенде (можно писать что угодно)
    category = models.CharField(
        'Категория (группа)', max_length=50, default='Системные',
        help_text="Например: Маркетинг, Записи, Бонусы"
    )
    
    # Флаги каналов доставки
    allow_push = models.BooleanField('Отправлять Push', default=True)
    allow_sms = models.BooleanField('Отправлять SMS', default=False, 
                                    help_text="Внимание: SMS стоит денег!")
    
    default_enabled = models.BooleanField('Включено по умолчанию', default=True)
    is_active = models.BooleanField('Активно', default=True)

    class Meta:
        verbose_name = 'Тип уведомления'
        verbose_name_plural = 'Типы уведомлений'
        ordering = ['category', 'name']

    def __str__(self):
        return f"[{self.category}] {self.name}"


class ClientNotificationSetting(models.Model):
    client = models.ForeignKey('booking_app.Client', on_delete=models.CASCADE, related_name='notification_settings')
    notification_type = models.ForeignKey(NotificationType, on_delete=models.CASCADE, related_name='client_settings')
    is_enabled = models.BooleanField('Включено', default=True)

    class Meta:
        verbose_name = 'Настройка уведомления клиента'
        verbose_name_plural = 'Настройки уведомлений клиентов'
        unique_together = ('client', 'notification_type')

    def __str__(self):
        return f"{self.client} — {self.notification_type.name} ({self.is_enabled})"