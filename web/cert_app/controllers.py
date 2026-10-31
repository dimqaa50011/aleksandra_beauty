import re
from datetime import datetime
from io import BytesIO
from django.core.files.base import ContentFile
from django.utils import timezone
from dateutil.relativedelta import relativedelta

import jwt
import qrcode

from .models import CertificateModel
from booking_app.models import Client
# Импортируем нашу функцию отправки СМС из booking_app
from booking_app.sms_service import send_sms


class CertController:
    def __init__(self, secret_key: str):
        self._secret = secret_key
    
    def _normalize_phone(self, phone: str) -> str:
        """Нормализация номера телефона (на случай, если в базе он записан криво)"""
        if not phone:
            return phone
        phone = re.sub(r'[\s\(\)\-\.]', '', phone)
        if phone.startswith('8'):
            phone = '+7' + phone[1:]
        elif phone.startswith('9') and len(phone) == 10:
            phone = '+7' + phone
        elif phone.startswith('7') and not phone.startswith('+7'):
            phone = '+' + phone
        return phone
    
    # =============================================
    # СОЗДАНИЕ СЕРТИФИКАТА
    # =============================================
    def create_new_cert(
        self, 
        client: Client, # <-- Теперь принимаем объект клиента
        price: int, 
        need_qr: bool = True
    ):
        if not client:
            raise ValueError("Клиент не передан в контроллер")

        phone = self._normalize_phone(client.phone)
        email = client.email or ""
        client_name = client.name or "Клиент"
        
        token = jwt.encode(
            {"phone": phone, "email": email, "exp": datetime.now() + relativedelta(years=1)},
            self._secret, 
            algorithm="HS256"
        )
        
        qr_code = None
        if need_qr:
            qr_code = self.make_qr(token)
        
        # Создаем сертификат, привязывая его к клиенту
        crt = CertificateModel.objects.create(
            client=client, # <-- Привязка
            phone=phone,
            email=email,
            client_name=client_name,
            expire_date=timezone.now().date() + relativedelta(years=1),
            price=price,
            token=token,
            qr_code=qr_code
        )
        
        # Вызываем универсальный метод уведомления
        self.notify_client(crt)
        return crt

    # =============================================
    # УВЕДОМЛЕНИЯ (СНАЧАЛА СМС, ПОТОМ МОЖНО ДОБАВИТЬ ДРУГОЕ)
    # =============================================
    def notify_client(self, certificate: CertificateModel):
        """
        Универсальный метод оповещения клиента.
        Сейчас отправляет только СМС. В будущем сюда можно добавить Telegram/WhatsApp.
        """
        # 1. Отправка по СМС
        if certificate.phone:
            sms_text = (
                f"Здравствуйте, {certificate.client_name}! "
                f"Ваш подарочный сертификат на {certificate.price} ₽ готов. "
                f"Код: {certificate.token[:8]}. "
                f"Действует до {certificate.expire_date.strftime('%d.%m.%Y')}."
            )
            try:
                # Отправляем через наш сервис
                send_sms(certificate.phone, sms_text)
                print(f"✅ SMS с сертификатом отправлена на {certificate.phone}")
            except Exception as e:
                print(f"❌ Ошибка отправки SMS: {e}")

        # 2. Задел на будущее (Email/Telegram)
        # if certificate.email:
        #     self.send_certificate_email(certificate)
        
    # =============================================
    # ОСТАЛЬНЫЕ МЕТОДЫ (БЕЗ ИЗМЕНЕНИЙ)
    # =============================================
    def find_by_token(self, token: str):
        return CertificateModel.objects.filter(token=token, is_used=False).first()
    
    def find_by_phone(self, phone: str):
        phone = self._normalize_phone(phone)
        return CertificateModel.objects.filter(phone=phone, is_used=False)
    
    def find_all_by_phone(self, phone: str):
        phone = self._normalize_phone(phone)
        return CertificateModel.objects.filter(phone=phone)
    
    def find_by_id(self, pk: int):
        return CertificateModel.objects.filter(pk=pk).first()
    
    def redeem_by_phone(self, phone: str):
        phone = self._normalize_phone(phone)
        certificates = self.find_by_phone(phone)
        if not certificates.exists():
            raise ValueError(f"Активных сертификатов для номера {phone} не найдено")
        
        redeemed_count = 0
        for cert in certificates:
            cert.use()
            redeemed_count += 1
        return redeemed_count
    
    def redeem_by_id(self, pk: int):
        crt = self.find_by_id(pk)
        if not crt:
            raise ValueError("Сертификат не найден")
        if crt.is_used:
            raise ValueError("Сертификат уже погашен")
        crt.use()
        return crt
    
    def make_qr(self, data: str):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        image_file = ContentFile(buffer.read(), name=f"qr_{data[:8]}.png")
        return image_file
    
    def get_statistics(self):
        total = CertificateModel.objects.count()
        active = CertificateModel.objects.filter(
            is_used=False, 
            expire_date__gte=timezone.now().date()
        ).count()
        redeemed = CertificateModel.objects.filter(is_used=True).count()
        expired = CertificateModel.objects.filter(
            is_used=False, 
            expire_date__lt=timezone.now().date()
        ).count()
        
        return {
            'total': total,
            'active': active,
            'redeemed': redeemed,
            'expired': expired,
        }
    
    def get_all_certificates(self):
        return CertificateModel.objects.all()
    
    def delete_certificate(self, pk: int):
        crt = self.find_by_id(pk)
        if crt:
            crt.delete()
            return True
        return False
    
    def get_nominals(self):
        from .models import CertificateNominal
        return CertificateNominal.objects.filter(is_active=True).values_list('value', flat=True)