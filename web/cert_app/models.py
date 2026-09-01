from datetime import datetime
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone


class CertificateNominal(models.Model):
    """Модель для фиксированных номиналов сертификатов"""
    value = models.PositiveIntegerField("Номинал (₽)", unique=True)
    is_active = models.BooleanField("Активен", default=True)
    order = models.PositiveIntegerField("Порядок", default=0)
    
    class Meta:
        ordering = ['order', 'value']
        verbose_name = "Номинал сертификата"
        verbose_name_plural = "Номиналы сертификатов"
    
    def __str__(self):
        return f"{self.value} ₽"


class CertificateModel(models.Model):
    """Подарочный сертификат"""
    
    phone = models.CharField("Телефон", max_length=16)
    email = models.CharField("Почта", max_length=128)
    expire_date = models.DateField("Действует до:")
    is_used = models.BooleanField("Использован?", default=False)
    price = models.PositiveIntegerField("На сумму:")
    used_date = models.DateTimeField("Дата использования", blank=True, null=True)
    token = models.CharField(max_length=128, unique=True)
    qr_code = models.ImageField(blank=True, null=True)
    email_sended = models.BooleanField("Отправлен на почту?", default=False)
    
    # Дополнительно
    client_name = models.CharField("Имя клиента", max_length=100, blank=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    
    class Meta:
        verbose_name = "Сертификат"
        verbose_name_plural = "Сертификаты"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Сертификат #{self.token[:8]} — {self.email}"
    
    def use(self):
        if not self.is_used:
            self.is_used = True
            self.used_date = timezone.now()
            self.save()
            return True
        return False
    
    def send_email(self, subject="Ваш подарочный сертификат", message=None):
        try:
            if not message:
                message = f"""
                Здравствуйте!
                
                Ваш подарочный сертификат №{self.token[:8]}
                Номинал: {self.price} ₽
                Действует до: {self.expire_date.strftime('%d.%m.%Y')}
                
                Для использования предъявите этот код: {self.token}
                
                С уважением,
                Glowora Beauty Studio
                """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=None,
                recipient_list=[self.email],
                fail_silently=False,
            )
            self.email_sended = True
            self.save()
            return True
        except Exception as e:
            print(f"Ошибка отправки письма: {e}")
            return False