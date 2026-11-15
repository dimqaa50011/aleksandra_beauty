from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from rest_framework.response import Response

from booking_app.models import BonusBalance

from .base import CabinetAPIView
from ..serializers.bonuses import (
    BonusTransactionSerializer,
    CashbackRuleSerializer,
    CertificateSerializer,
)
from ..models import BonusTransaction, CashbackRule
from booking_app.utils import phone_variants
from cert_app.models import CertificateModel
from datetime import timedelta

class BonusesView(CabinetAPIView):
    """GET: Баланс, список сгорающих бонусов, история транзакций, активные правила кэшбэка."""

    def get(self, request):
        client = request.user.client
        
        # 1. Получаем кошелек клиента
        wallet, _ = BonusBalance.objects.get_or_create(client=client)
        
        # 2. Считаем общий баланс (сумма всех активных бонусов)
        total_balance = wallet.get_total()
        
        # 3. Ищем бонусы, которые скоро сгорят
        # Берем только не потраченные и не сгоревшие, срок которых истекает в ближайшие 30 дней
        now = timezone.now()
        threshold = now + timedelta(days=30)
        
        expiring_bonuses_qs = wallet.bonuses.filter(
            is_spent=False,
            is_expired=False,
            expires_at__gt=now,
            expires_at__lte=threshold
        ).order_by('expires_at')

        expiring_list = []
        for bonus in expiring_bonuses_qs:
            days_left = (bonus.expires_at - now).days
            
            # Красивое название причины для клиента
            reasons_map = {
                'cashback': 'Кэшбэк',
                'referral': 'Бонус за друга',
                'promo': 'Акция',
                'migration': 'Старые бонусы',
            }
            reason_text = reasons_map.get(bonus.reason, bonus.reason)

            expiring_list.append({
                'amount': bonus.amount,
                'expires_at': bonus.expires_at.strftime('%d.%m.%Y'),
                'days_left': days_left,
                'reason': reason_text
            })

        # 4. 50 последних транзакций (история начислений/списаний)
        transactions = BonusTransaction.objects.filter(
            client=client
        ).order_by('-created_at')[:50]
        
        # 5. Активные правила кэшбэка на сегодня
        today = timezone.localdate()
        rules = CashbackRule.objects.filter(
            is_active=True,
            valid_from__lte=today,
            valid_until__gte=today
        ).select_related('service').order_by('service__name')

        return Response({
            'balance': total_balance,
            'expiring_soon': expiring_list,  # <--- СПИСОК СГОРАЮЩИХ БОНУСОВ
            'max_spend_percent': settings.CABINET_MAX_BONUS_SPEND_PERCENT,
            'transactions': BonusTransactionSerializer(transactions, many=True).data,
            'cashback_rules': CashbackRuleSerializer(rules, many=True).data,
        })

from rest_framework.exceptions import NotFound

class CertificatesView(CabinetAPIView):
    """GET: Список сертификатов клиента."""
    def get(self, request):
        client = request.user.client
        
        variants = phone_variants(client.phone)
        qs = CertificateModel.objects.filter(
            Q(client=client) | Q(client__isnull=True, phone__in=variants)
        ).order_by('-created_at')

        # Фильтр по параметру (например, ?active=true)
        active_only = request.query_params.get('active') == 'true'
        if active_only:
            qs = qs.filter(is_used=False, expire_date__gte=timezone.localdate())

        return Response({
            'certificates': CertificateSerializer(qs, many=True).data
        })


class CertificateDetailView(CabinetAPIView):
    """GET: Детали одного сертификата."""
    def get(self, request, pk):
        client = request.user.client
        variants = phone_variants(client.phone)
        
        cert = CertificateModel.objects.filter(
            Q(id=pk) & (Q(client=client) | Q(client__isnull=True, phone__in=variants))
        ).first()
        
        if not cert:
            raise NotFound('Сертификат не найден')
            
        return Response(CertificateSerializer(cert).data)

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
            'link': f'https://sasha-sugar.ru/cabinet/register?ref={user.referral_code}',
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