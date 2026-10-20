from rest_framework import serializers
from .models import Booking

class ServiceShortSerializer(serializers.Serializer):
    """Краткая информация об услуге для списка записей"""
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=0)


class BookingSerializer(serializers.ModelSerializer):
    """Сериализатор для вывода записей в мобильное приложение"""
    time = serializers.TimeField(source='appointment_datetime', format='%H:%M', read_only=True)
    services = ServiceShortSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'client_name', 'phone', 'time', 
            'services', 'total_price', 'status', 'status_display'
        ]

    def get_total_price(self, obj):
        """Считаем сумму всех услуг в записи"""
        return sum(service.price for service in obj.services.all())


class BlockDaySerializer(serializers.Serializer):
    """Сериализатор для валидации данных при блокировке дня"""
    date = serializers.DateField(required=True)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=100)