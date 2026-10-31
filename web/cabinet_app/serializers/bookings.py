from rest_framework import serializers

from booking_app.models import Booking


class ServiceShortSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    duration = serializers.IntegerField()


class BookingListSerializer(serializers.ModelSerializer):
    services = serializers.SerializerMethodField()
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    can_cancel = serializers.SerializerMethodField()
    can_reschedule = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'appointment_datetime', 'status', 'status_display',
            'services', 'total_price', 'use_bonuses_requested',
            'bonuses_to_apply', 'bonuses_applied', 'cashback_accrued',
            'can_cancel', 'can_reschedule',
        ]

    def get_services(self, obj):
        return ServiceShortSerializer(obj.services.all(), many=True).data

    def _can_modify(self, obj):
        if obj.status not in ('pending', 'confirmed'):
            return False
        from django.utils import timezone
        return (obj.appointment_datetime - timezone.now()).total_seconds() >= 3 * 3600

    def get_can_cancel(self, obj):
        return self._can_modify(obj)

    def get_can_reschedule(self, obj):
        return self._can_modify(obj)


class BookingDetailSerializer(BookingListSerializer):
    certificate = serializers.SerializerMethodField()

    class Meta(BookingListSerializer.Meta):
        fields = BookingListSerializer.Meta.fields + [
            'certificate', 'rescheduled_from',
            'cancel_reason', 'cancel_reason_text', 'cancelled_at',
        ]

    def get_certificate(self, obj):
        cert = obj.reserved_certificates.filter(is_used=False).first()
        if cert is None:
            cert = obj.used_certificates.first()
        if cert is None:
            return None
        return {
            'id': cert.pk,
            'code_prefix': cert.token[:8],
            'price': cert.price,
            'is_used': cert.is_used,
            'expire_date': cert.expire_date.isoformat(),
        }


class BookingCreateSerializer(serializers.Serializer):
    service_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1, max_length=10,
    )
    appointment_datetime = serializers.DateTimeField()
    use_bonuses = serializers.BooleanField(default=False)
    bonuses_to_apply = serializers.IntegerField(default=0, min_value=0)
    certificate_id = serializers.IntegerField(required=False, allow_null=True)


class BookingCancelSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(choices=[
        ('sick', 'Болею'),
        ('plans_changed', 'Планы изменились'),
        ('cant_make_it', 'Не смогу прийти'),
        ('other', 'Другое'),
    ])
    reason_text = serializers.CharField(required=False, allow_blank=True, max_length=255)


class BookingRescheduleSerializer(serializers.Serializer):
    new_datetime = serializers.DateTimeField()