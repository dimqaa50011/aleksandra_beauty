from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, time as dt_time

# Импортируем модели из нового приложения и старого каталога
from .models import Booking, BlockedSlot
from beauty_app.models import Service, ServiceCategory


# =============================================
# КОНСТАНТЫ ВРЕМЕНИ
# =============================================
# С 9:00 до 22:30 с шагом 30 минут (последний слот для начала, чтобы успеть до 23:00)
ALL_TIME_CHOICES = [
    (f"{h:02d}:{m:02d}", f"{h:02d}:{m:02d}") 
    for h in range(9, 23)
    for m in (0, 30)
]

TIME_CHOICES = ALL_TIME_CHOICES # Используем тот же список для формы блокировки


# =============================================
# ФОРМЫ ЗАПИСИ
# =============================================
class BookingForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=ServiceCategory.objects.filter(is_active=True),
        required=False,
        empty_label="Выберите категорию",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    appointment_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control', 
            'min': timezone.now().date().isoformat()
        }),
        label='Дата'
    )
    
    appointment_time = forms.ChoiceField(
        choices=ALL_TIME_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True,
        label='Время'
    )
    
    # Явно делаем Email обязательным для верификации
    email = forms.EmailField(
        label='Email для подтверждения',
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 
            'placeholder': 'example@mail.ru',
            'id': 'id_email_input' # Важно для JS проверки
        })
    )

    class Meta:
        model = Booking
        fields = ['client_name', 'phone', 'email', 'service', 'category']
        widgets = {
            'client_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ваше имя'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (999) 123-45-67'}),
            'service': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'initial' in kwargs and 'service' in kwargs['initial']:
            self.fields['service'].queryset = Service.objects.filter(id=kwargs['initial']['service'].id)
            self.fields['service'].empty_label = None

    def clean(self):
        # Импортируем внутри метода, чтобы избежать циклического импорта с views.py
        from .views import is_time_slot_available 
        
        cleaned_data = super().clean()
        date = cleaned_data.get('appointment_date')
        time_str = cleaned_data.get('appointment_time')
        service = cleaned_data.get('service')

        if date and time_str and service:
            try:
                naive_dt = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M")
                aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
                
                if not is_time_slot_available(aware_dt, service):
                    self.add_error(
                        'appointment_time', 
                        'Это время уже занято или заблокировано. Пожалуйста, выберите другое.'
                    )
            except ValueError:
                self.add_error('appointment_time', 'Неверный формат времени.')

        return cleaned_data


class AdminBookingForm(BookingForm):
    """Форма для ручного создания записи админом (добавляет выбор статуса)"""
    status = forms.ChoiceField(
        choices=Booking.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Статус',
        initial='confirmed'
    )


# =============================================
# ФОРМЫ АДМИНИСТРИРОВАНИЯ СЛОТОВ
# =============================================
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Booking # Убедись, что это есть в импортах вверху файла
class BlockedSlotForm(forms.ModelForm):
    """Форма для добавления заблокированного слота"""
    
    class Meta:
        model = BlockedSlot
        fields = ['date', 'is_full_day', 'start_time', 'end_time', 'slot_type', 'reason']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control',
                'id': 'id_block_date'
            }),
            'is_full_day': forms.CheckboxInput(attrs={
                'class': 'form-check-input', 
                'id': 'id_is_full_day'
            }),
            'start_time': forms.Select(attrs={'class': 'form-control', 'id': 'id_start_time'}),
            'end_time': forms.Select(attrs={'class': 'form-control', 'id': 'id_end_time'}),
            'slot_type': forms.Select(attrs={'class': 'form-control'}),
            'reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Причина (необязательно)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start_time'].required = False
        self.fields['end_time'].required = False
        # Начальные choices пустые — заполняются через JavaScript
        self.fields['start_time'].choices = [('', 'Сначала выберите дату')]
        self.fields['end_time'].choices = [('', 'Сначала выберите дату')]

    def clean(self):
        cleaned_data = super().clean()
        is_full_day = cleaned_data.get('is_full_day')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if not is_full_day:
            if not start_time or not end_time:
                raise forms.ValidationError("Если не выбрано 'На весь день', укажите время начала и конца.")
            if start_time >= end_time:
                raise forms.ValidationError("Время начала должно быть раньше времени конца.")

        return cleaned_data