from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from rest_framework.response import Response

from .base import CabinetAPIView
from ..serializers.bonuses import (
    BonusTransactionSerializer,
    CashbackRuleSerializer,
    CertificateSerializer,
)
from ..models import BonusTransaction, CashbackRule
from booking_app.utils import phone_variants
from cert_app.models import CertificateModel


class BonusesView(CabinetAPIView):
    """GET: Баланс, история транзакций, активные правила кэшбэка."""

    def get(self, request):
        client = request.user.client
        
        # 50 последних транзакций
        transactions = BonusTransaction.objects.filter(
            client=client
        ).order_by('-created_at')[:50]
        
        # Активные правила кэшбэка на сегодня
        today = timezone.localdate()
        rules = CashbackRule.objects.filter(
            is_active=True,
            valid_from__lte=today,
            valid_until__gte=today
        ).select_related('service').order_by('service__name')

        return Response({
            'balance': client.bonus_balance,
            'max_spend_percent': settings.CABINET_MAX_BONUS_SPEND_PERCENT,
            'transactions': BonusTransactionSerializer(transactions, many=True).data,
            'cashback_rules': CashbackRuleSerializer(rules, many=True).data,
        })


class CertificatesView(CabinetAPIView):
    """GET: Список сертификатов клиента."""

    def get(self, request):
        client = request.user.client
        
        # Ищем сертификаты по прямой привязке или по телефону
        variants = phone_variants(client.phone)
        certs = CertificateModel.objects.filter(
            Q(client=client) | Q(client__isnull=True, phone__in=variants)
        ).order_by('-created_at')

        return Response({
            'certificates': CertificateSerializer(certs, many=True).data
        })

from ..models import Referral # добавь в импорты наверху

class ReferralView(CabinetAPIView):
    """GET: Реферальная ссылка и статистика приглашений."""
    def get(self, request):
        user = request.user
        
        # Если у пользователя еще нет реф-кода, генерируем
        if not user.referral_code:
            user.referral_code = user.generate_referral_code()
            user.save(update_fields=['referral_code'])
            
        referrals = Referral.objects.filter(referrer=user.client).select_related('referee')
        
        return Response({
            'code': user.referral_code,
            # Ссылка на фронтенд с параметром ref
            'link': f'https://cabinet.sasha-sugar.ru/register?ref={user.referral_code}',
            'invited_count': referrals.count(),
            'rewarded_count': referrals.filter(status=Referral.STATUS_REWARDED).count(),
            'referrals': [
                {
                    'name': r.referee.name.split(' ')[0] if r.referee.name else 'Друг',
                    'status': r.get_status_display(),
                    'registered_at': r.registered_at.strftime('%d.%m.%Y'),
                } for r in referrals
            ]
        })