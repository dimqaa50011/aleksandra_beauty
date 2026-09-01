from django import forms
from .models import CertificateNominal


class CertificateForm(forms.Form):
    """Форма для создания сертификата"""
    
    price = forms.ChoiceField(
        label='Номинал (₽)',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    phone = forms.CharField(
        max_length=16,
        label='Телефон',
        widget=forms.TextInput(attrs={
            'placeholder': '+7 (999) 123-45-67',
            'class': 'form-control'
        })
    )
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'placeholder': 'client@example.com',
            'class': 'form-control'
        })
    )
    client_name = forms.CharField(
        max_length=100,
        label='Имя клиента',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Анна Иванова',
            'class': 'form-control'
        })
    )
    need_qr = forms.BooleanField(
        label='Сгенерировать QR-код',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        nominals = CertificateNominal.objects.filter(is_active=True)
        choices = [(str(n.value), f"{n.value} ₽") for n in nominals]
        if not choices:
            choices = [('', '--- Нет доступных номиналов ---')]
        self.fields['price'].choices = choices


class RedeemForm(forms.Form):
    """Форма для поиска сертификатов по телефону"""
    phone = forms.CharField(
        max_length=32,
        label='Номер телефона',
        widget=forms.TextInput(attrs={
            'placeholder': '+7 (999) 123-45-67',
            'class': 'form-control'
        })
    )


class RedeemSelectForm(forms.Form):
    """Форма для выбора сертификата для погашения"""
    certificate_id = forms.ChoiceField(
        label='Выберите сертификат',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        certificates = kwargs.pop('certificates', [])
        super().__init__(*args, **kwargs)
        choices = [(str(c.id), f"{c.client_name} — {c.price} ₽ (до {c.expire_date.strftime('%d.%m.%Y')})") for c in certificates]
        if not choices:
            choices = [('', '--- Нет активных сертификатов ---')]
        self.fields['certificate_id'].choices = choices