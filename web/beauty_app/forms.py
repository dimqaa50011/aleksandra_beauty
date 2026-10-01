from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Booking, Service, ServiceCategory
from django.utils import timezone

from .models import BlockedSlot


# =============================================
# ФОРМЫ ДЛЯ АДМИНКИ
# =============================================



class LoginForm(AuthenticationForm):
    """Форма входа в стиле бренда"""
    
    username = forms.CharField(
        label='Логин',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите логин',
            'autofocus': True
        })
    )
    
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )
    
    error_messages = {
        'invalid_login': 'Неверный логин или пароль.',
        'inactive': 'Аккаунт отключён.',
    }


from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime
from .models import Booking, Service, ServiceCategory
# Импортируем нашу функцию проверки

# Оставляем список всех возможных слотов, чтобы Django не ругался на формат
ALL_TIME_CHOICES = [
    (f"{h:02d}:{m:02d}", f"{h:02d}:{m:02d}") 
    for h in range(0, 24) 
    for m in (0, 30)
]

class BookingForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=ServiceCategory.objects.filter(is_active=True),
        required=False,
        empty_label="Выберите категорию",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    appointment_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'min': timezone.now().date().isoformat()}),
        label='Дата'
    )
    
    appointment_time = forms.ChoiceField(
        choices=ALL_TIME_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
        label='Время'
    )

    class Meta:
        model = Booking
        fields = ['client_name', 'phone', 'email', 'service', 'category']
        widgets = {
            'client_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ваше имя'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (999) 123-45-67'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'service': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'initial' in kwargs and 'service' in kwargs['initial']:
            self.fields['service'].queryset = Service.objects.filter(id=kwargs['initial']['service'].id)
            self.fields['service'].empty_label = None

    # === ВОТ ЗДЕСЬ МАГИЯ ===
    def clean(self):
        from .views import is_time_slot_available 
        cleaned_data = super().clean()
        
        # Получаем данные из формы
        date = cleaned_data.get('appointment_date')
        time_str = cleaned_data.get('appointment_time')
        service = cleaned_data.get('service')

        # Если все три поля заполнены, проверяем их вместе
        if date and time_str and service:
            try:
                # Собираем дату и время в один объект datetime
                naive_dt = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M")
                aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
                
                # Проверяем через нашу функцию, свободен ли слот
                if not is_time_slot_available(aware_dt, service):
                    # Если занят, добавляем ошибку прямо к полю "Время"
                    self.add_error(
                        'appointment_time', 
                        'Это время уже занято или заблокировано. Пожалуйста, выберите другое.'
                    )
            except ValueError:
                self.add_error('appointment_time', 'Неверный формат времени.')

        return cleaned_data

from datetime import time as dt_time

# Генерируем список времени с 00:00 до 23:30 с шагом 30 минут
TIME_CHOICES = [
    (f"{h:02d}:{m:02d}", f"{h:02d}:{m:02d}") 
    for h in range(0, 24) 
    for m in (0, 30)
]

class BlockedSlotForm(forms.Form):
    """Форма для добавления заблокированного слота"""
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Дата'
    )
    
    # Выпадающие списки вместо полей ввода
    start_time = forms.ChoiceField(
        choices=TIME_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Начало'
    )
    
    end_time = forms.ChoiceField(
        choices=TIME_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Конец'
    )
    
    slot_type = forms.ChoiceField(
        choices=BlockedSlot.TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Тип'
    )
    
    reason = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Причина (необязательно)'}),
        label='Причина'
    )


class AdminBookingForm(BookingForm):
    """Форма для ручного создания записи админом"""
    status = forms.ChoiceField(
        choices=Booking.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Статус',
        initial='confirmed'
    )