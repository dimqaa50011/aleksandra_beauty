from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta

from booking_app.models import Client


class ClientProfileSerializer(serializers.ModelSerializer):
    # Поля из CabinetUser
    phone = serializers.CharField(source='cabinet_user.phone', read_only=True)
    consent_marketing = serializers.BooleanField(source='cabinet_user.consent_marketing', required=False)
    
    # Статистика
    years_with_us = serializers.SerializerMethodField()
    favorite_service = serializers.SerializerMethodField()
    
    avatar = serializers.ImageField(source='cabinet_user.avatar', read_only=True)

    class Meta:
        model = Client
        fields = [
            'id', 'name', 'email', 'phone', 'avatar',
            'bonus_balance', 'total_bookings', 'total_spent', 
            'first_visit', 'last_visit',
            'consent_marketing', 'years_with_us', 'favorite_service'
        ]
        read_only_fields = [
            'id', 'phone', 'bonus_balance', 'total_bookings', 
            'total_spent', 'first_visit', 'last_visit', 
            'years_with_us', 'favorite_service'
        ]

    def get_years_with_us(self, obj):
        """Сколько лет клиент с нами (для красивой плашки)."""
        if not obj.first_visit:
            return 0
        delta = timezone.now() - obj.first_visit
        return delta.days // 365

    def get_favorite_service(self, obj):
        """Самая часто посещаемая услуга (для статистики)."""
        from django.db.models import Count
        from beauty_app.models import Service
        
        # Берем самую частую услугу из завершенных визитов
        fav = Service.objects.filter(
            bookings__client=obj,
            bookings__status='completed'
        ).annotate(
            visit_count=Count('bookings')
        ).order_by('-visit_count').first()
        
        if fav:
            return {'id': fav.id, 'name': fav.name, 'count': fav.visit_count}
        return None