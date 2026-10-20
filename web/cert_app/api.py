from ninja import NinjaAPI
from django.conf import settings



from cert_app.schemas import CreateCertSchema
from .controllers import CertController
from .auth import AuthBearer

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import CertificateModel


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import CertificateModel


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

class AdminCertificateCreateAPIView(APIView):
    """
    POST: Создать новый сертификат
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        phone = request.data.get('phone', '').strip()
        email = request.data.get('email', '').strip()
        price = request.data.get('price')
        client_name = request.data.get('client_name', '').strip()

        if not phone or not email or not price:
            return Response({'error': 'Заполните телефон, email и сумму'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            price_int = int(price)
        except ValueError:
            return Response({'error': 'Неверный формат суммы'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Используем ваш контроллер!
            certificate = cert_controller.create_new_cert(
                phone=phone,
                email=email,
                price=price_int,
                client_name=client_name,
                need_qr=False # В мобильном приложении QR пока не нужен
            )
            
            return Response({
                'success': True,
                'message': 'Сертификат создан и отправлен на почту!',
                'certificate': {
                    'id': certificate.id,
                    'token_short': certificate.token[:8]
                }
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Ошибка сервера: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminCertificatesListAPIView(APIView):
    """GET: Список всех сертификатов (последние 50)"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        certs = CertificateModel.objects.all().order_by('-created_at')[:50]
        data = []
        for c in certs:
            data.append({
                'id': c.id,
                'token_short': c.token[:8],
                'price': c.price,
                'client_name': c.client_name,
                'phone': c.phone,
                'email': c.email,
                'is_used': c.is_used,
                'expire_date': c.expire_date.strftime('%d.%m.%Y'),
            })
        return Response({'certificates': data})


class AdminCertificateRedeemAPIView(APIView):
    """
    POST: Гашение сертификата по номеру телефона.
    Если сертификатов несколько — возвращает их список для выбора.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        phone = request.data.get('phone', '').strip()
        cert_id = request.data.get('certificate_id')

        if not phone:
            return Response({'error': 'Введите номер телефона'}, status=status.HTTP_400_BAD_REQUEST)

        # Если передан ID — значит, админ уже выбрал конкретный сертификат из списка
        if cert_id:
            try:
                cert = CertificateModel.objects.get(id=cert_id, is_used=False)
                cert.use()
                return Response({'success': True, 'message': f'Сертификат {cert.token[:8]} погашен'})
            except CertificateModel.DoesNotExist:
                return Response({'error': 'Сертификат не найден или уже использован'}, status=404)

        # Ищем активные сертификаты по номеру
        certificates = CertificateModel.objects.filter(phone=phone, is_used=False)
        
        if not certificates.exists():
            return Response({'error': f'Активных сертификатов для номера {phone} не найдено'}, status=404)

        # Если один — гасим сразу
        if certificates.count() == 1:
            cert = certificates.first()
            cert.use()
            return Response({'success': True, 'message': f'Сертификат {cert.token[:8]} погашен'})

        # Если несколько — отдаем список для выбора
        choices = [{
            'id': c.id,
            'token_short': c.token[:8],
            'price': c.price,
            'expire_date': c.expire_date.strftime('%d.%m.%Y'),
            'client_name': c.client_name,
        } for c in certificates]

        return Response({
            'multiple': True,
            'certificates': choices,
            'message': 'У клиента несколько сертификатов. Выберите нужный.'
        })
class AdminCertificatesAPIView(APIView):
    """
    GET: Список последних сертификатов
    POST: Создать новый сертификат (если нужно)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        certs = CertificateModel.objects.all().order_by('-created_at')[:50]
        data = []
        for c in certs:
            data.append({
                'id': c.id,
                'token_short': c.token[:8], # Для отображения
                'token': c.token,           # Полный токен (если понадобится для QR)
                'price': c.price,
                'email': c.email,
                'phone': c.phone,
                'client_name': c.client_name,
                'is_used': c.is_used,
                'expire_date': c.expire_date.strftime('%d.%m.%Y'),
                'created_at': c.created_at.strftime('%d.%m.%Y'),
            })
        return Response({'certificates': data}, status=status.HTTP_200_OK)


class AdminCertificateUseAPIView(APIView):
    """
    POST: Погасить сертификат (отметить как использованный)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        cert = get_object_or_404(CertificateModel, pk=pk)
        
        if cert.is_used:
            return Response({'error': 'Сертификат уже использован'}, status=status.HTTP_400_BAD_REQUEST)
            
        success = cert.use()
        if success:
            return Response({'success': True, 'message': 'Сертификат погашен'}, status=status.HTTP_200_OK)
            
        return Response({'error': 'Ошибка при погашении'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

api = NinjaAPI(auth=AuthBearer())
cert_controller = CertController(settings.CERT_SECRET)

@api.get("/cert/get/{phone}")
def get_cert_by_phone(request, phone: str):
    ...

@api.post("/cert/use/{phone}")
def use_cert(request, phone: str):
    ...

@api.post("/cert/create")
def create_cert(requset, data: CreateCertSchema):
    new_crt = cert_controller.create_new_cert(data.phone, data.email, data.price)
    new_crt.send_email()
    
