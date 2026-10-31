from rest_framework.response import Response

from beauty_app.models import Service, ServiceCategory

from .base import CabinetAPIView


class ServiceListView(CabinetAPIView):
    def get(self, request):
        services = Service.objects.filter(is_active=True).select_related('category').order_by(
            'category__order', 'name',
        )
        data = []
        for s in services:
            data.append({
                'id': s.pk,
                'name': s.name,
                'price': str(s.price),
                'duration': s.duration or 0,
                'category_id': s.category_id,
                'category_name': s.category.name if s.category else 'Без категории',
            })
        return Response({'services': data})