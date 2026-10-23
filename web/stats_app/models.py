from django.db import models
from django.utils import timezone

class Expense(models.Model):
    """Модель для учета расходов студии"""
    amount = models.DecimalField('Сумма', max_digits=10, decimal_places=2)
    description = models.CharField('Описание', max_length=255)
    date = models.DateField('Дата расхода', default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Расход'
        verbose_name_plural = 'Расходы'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.date} — {self.description} ({self.amount} ₽)"