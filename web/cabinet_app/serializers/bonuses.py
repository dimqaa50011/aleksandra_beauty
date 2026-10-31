from rest_framework import serializers
from django.utils import timezone

from ..models import BonusTransaction, CashbackRule
from cert_app.models import CertificateModel


class BonusTransactionSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    reason_display = serializers.SerializerMethodField()

    class Meta:
        model = BonusTransaction
        fields = [
            'id', 'amount', 'type', 'type_display', 
            'reason', 'reason_display', 'description', 
            'balance_after', 'created_at'
        ]

    def get_reason_display(self, obj):
        reasons = {
            'visit': 'Оплата бонусами',
            'cashback': 'Кэшбэк за визит',
            'referral_registered': 'Бонус за друга (регистрация)',
            'referral_first_visit': 'Бонус за друга (первый визит)',
        }
        return reasons.get(obj.reason, obj.description or obj.reason)


class CashbackRuleSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source='service.name', read_only=True)

    class Meta:
        model = CashbackRule
        fields = ['id', 'service', 'service_name', 'percent', 'valid_until']


class CertificateSerializer(serializers.ModelSerializer):
    code = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()
    qr_code = serializers.ImageField(read_only=True)

    class Meta:
        model = CertificateModel
        fields = [
            'id', 'code', 'price', 'expire_date', 
            'is_used', 'used_date', 'status_display', 
            'is_available', 'created_at', 'qr_code'
        ]

    def get_code(self, obj):
        """Показываем префикс токена для UI."""
        return obj.token[:8].upper() if obj.token else '—'

    def get_status_display(self, obj):
        if obj.is_used:
            return 'Использован'
        if timezone.localdate() > obj.expire_date:
            return 'Истёк'
        if obj.reserved_for_booking_id:
            return 'Зарезервирован'
        return 'Активен'

    def get_is_available(self, obj):
        """Можно ли использовать для новой записи."""
        return (
            not obj.is_used 
            and timezone.localdate() <= obj.expire_date 
            and not obj.reserved_for_booking_id
        )