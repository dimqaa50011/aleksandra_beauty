from django import forms
from django.utils import timezone
from .models import Booking, BlockedSlot
from beauty_app.models import Service, ServiceCategory, Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, f"{i} ★") for i in range(5, 0, -1)]),
            'text': forms.Textarea(attrs={
                'rows': 4, 
                'placeholder': 'Поделитесь своими впечатлениями о визите...',
                'class': 'form-control'
            }),
        }

class BookingForm(forms.ModelForm):
    """Форма записи клиента"""
    
    category = forms.ModelChoiceField(
        queryset=ServiceCategory.objects.filter(is_active=True),
        required=False,
        empty_label="Выберите категорию",
        label="Категория",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    service = forms.ModelChoiceField(
        queryset=Service.objects.filter(is_active=True),
        required=False,
        empty_label="----------",
        label="Услуга",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    appointment_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
        }),
        label="Дата"
    )
    
    # === ИЗМЕНЕНО: CharField вместо ChoiceField ===
    appointment_time = forms.CharField(
        max_length=5,
        required=False,
        label="Время",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Booking
        fields = ['client_name', 'phone', 'email']
        widgets = {
            'client_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ваше имя'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+7 (999) 123-45-67'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@mail.ru'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Для клиентов запрещаем выбирать прошлые даты
        self.fields['appointment_date'].widget.attrs['min'] = timezone.localdate().isoformat()

    def clean_appointment_time(self):
        """Ручная валидация формата времени"""
        time_str = self.cleaned_data.get('appointment_time', '')
        if time_str:
            try:
                from datetime import datetime
                datetime.strptime(time_str, '%H:%M')
            except ValueError:
                raise forms.ValidationError('Неверный формат времени. Используйте ЧЧ:ММ')
        return time_str


class AdminBookingForm(forms.ModelForm):
    """Форма для админки"""
    
    category = forms.ModelChoiceField(
        queryset=ServiceCategory.objects.filter(is_active=True),
        required=False,
        empty_label="Выберите категорию",
        label="Категория",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    service = forms.ModelChoiceField(
        queryset=Service.objects.filter(is_active=True),
        required=False,
        empty_label="----------",
        label="Услуга",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    appointment_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label="Дата"
    )
    
    # === ИЗМЕНЕНО: CharField вместо ChoiceField ===
    appointment_time = forms.CharField(
        max_length=5,
        required=False,
        label="Время",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Booking
        fields = ['client_name', 'phone', 'email']
        widgets = {
            'client_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean_appointment_time(self):
        time_str = self.cleaned_data.get('appointment_time', '')
        if time_str:
            try:
                from datetime import datetime
                datetime.strptime(time_str, '%H:%M')
            except ValueError:
                raise forms.ValidationError('Неверный формат времени')
        return time_str


class BlockedSlotForm(forms.ModelForm):
    class Meta:
        model = BlockedSlot
        fields = ['date', 'is_full_day', 'start_time', 'end_time', 'slot_type', 'reason']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'slot_type': forms.Select(attrs={'class': 'form-control'}),
            'reason': forms.TextInput(attrs={'class': 'form-control'}),
        }