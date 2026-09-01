import re
from datetime import datetime
from io import BytesIO
from django.core.files.base import ContentFile
from django.utils import timezone
from dateutil.relativedelta import relativedelta

import jwt
import qrcode

from .models import CertificateModel


class CertController:
    def __init__(self, secret_key: str):
        self._secret = secret_key
    
    # =============================================
    # НОРМАЛИЗАЦИЯ ТЕЛЕФОНА
    # =============================================
    def _normalize_phone(self, phone: str) -> str:
        """
        Нормализует номер телефона:
        - Удаляет все пробелы, скобки, дефисы
        - Если начинается с 8, заменяет на +7
        - Если начинается с 9 (без кода), добавляет +7
        - Если уже +7 — оставляет как есть
        """
        if not phone:
            return phone
        
        # Удаляем все пробелы, скобки, дефисы, точки
        phone = re.sub(r'[\s\(\)\-\.]', '', phone)
        
        # Если номер начинается с 8 — заменяем на +7
        if phone.startswith('8'):
            phone = '+7' + phone[1:]
        
        # Если номер начинается с 9 (типичный российский номер без кода)
        elif phone.startswith('9') and len(phone) == 10:
            phone = '+7' + phone
        
        # Если номер начинается с 7 (без +) — добавляем +
        elif phone.startswith('7') and not phone.startswith('+7'):
            phone = '+' + phone
        
        return phone
    
    # =============================================
    # ОСТАЛЬНЫЕ МЕТОДЫ (с использованием нормализации)
    # =============================================
    def create_new_cert(
        self, 
        phone: str, 
        email: str, 
        price: int, 
        client_name: str = "",
        need_qr: bool = False
    ):
        # Нормализуем телефон
        phone = self._normalize_phone(phone)
        
        token = jwt.encode(
            {"phone": phone, "email": email, "exp": datetime.now() + relativedelta(years=1)},
            self._secret, 
            algorithm="HS256"
        )
        
        qr_code = None
        if need_qr:
            qr_code = self.make_qr(token)
        
        crt = CertificateModel.objects.create(
            phone=phone,
            email=email,
            client_name=client_name,
            expire_date=timezone.now().date() + relativedelta(years=1),
            price=price,
            token=token,
            qr_code=qr_code
        )
        
        self.send_certificate_email(crt)
        return crt
    
    def find_by_token(self, token: str):
        return CertificateModel.objects.filter(token=token, is_used=False).first()
    
    def find_by_phone(self, phone: str):
        """Найти все активные сертификаты по телефону (с нормализацией)"""
        phone = self._normalize_phone(phone)
        return CertificateModel.objects.filter(phone=phone, is_used=False)
    
    def find_all_by_phone(self, phone: str):
        """Найти все сертификаты по телефону (включая использованные)"""
        phone = self._normalize_phone(phone)
        return CertificateModel.objects.filter(phone=phone)
    
    def find_by_id(self, pk: int):
        return CertificateModel.objects.filter(pk=pk).first()
    
    def redeem_by_phone(self, phone: str):
        """Погасить все активные сертификаты по телефону"""
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
        """Погасить конкретный сертификат по ID"""
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
    
    def send_certificate_email(self, certificate):
        try:
            from django.core.mail import send_mail
            
            message = f"""
            Здравствуйте!
            
            Ваш подарочный сертификат №{certificate.token[:8]}
            Номинал: {certificate.price} ₽
            Действует до: {certificate.expire_date.strftime('%d.%m.%Y')}
            
            Для использования предъявите этот код: {certificate.token}
            
            С уважением,
            Glowora Beauty Studio
            """
            
            send_mail(
                subject="Ваш подарочный сертификат",
                message=message,
                from_email=None,
                recipient_list=[certificate.email],
                fail_silently=False,
            )
            certificate.email_sended = True
            certificate.save()
            return True
        except Exception as e:
            print(f"Ошибка отправки письма: {e}")
            return False
    
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