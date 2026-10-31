from datetime import datetime

from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from beauty_app.models import Service
from booking_app.services.slots import (
    calculate_services_duration, get_available_slots,
)

from .base import CabinetAPIView


class SlotListView(CabinetAPIView):
    def get(self, request):
        date_str = request.query_params.get('date')
        service_ids_str = request.query_params.get('service_ids', '')

        if not date_str:
            raise ValidationError({'date': 'Обязательный параметр'})
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValidationError({'date': 'Ожидается YYYY-MM-DD'})

        if target_date < timezone.localdate():
            return Response({'times': [], 'is_blocked': False, 'is_past': True})

        duration = 60
        if service_ids_str:
            try:
                ids = [int(x) for x in service_ids_str.split(',') if x]
            except ValueError:
                raise ValidationError({'service_ids': 'Неверный формат'})
            services = Service.objects.filter(id__in=ids, is_active=True)
            if services.exists():
                duration = calculate_services_duration(services)

        result = get_available_slots(target_date, duration, apply_lead_time=True)
        result['is_past'] = False
        return Response(result)