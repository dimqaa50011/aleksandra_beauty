from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Service, ServiceCategory

class AdminServicesAPIView(APIView):
    """
    GET: Список всех услуг с категориями
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        categories = ServiceCategory.objects.filter(is_active=True).prefetch_related('services')
        
        data = []
        for cat in categories:
            services = cat.services.filter(is_active=True).order_by('order')
            if not services.exists():
                continue
                
            data.append({
                'category_id': cat.id,
                'category_name': cat.display_name,
                'services': [{
                    'id': s.id,
                    'name': s.display_name,
                    'price': s.price,
                    'duration': s.duration,
                } for s in services]
            })
            
        return Response({'categories': data}, status=status.HTTP_200_OK)


class AdminServiceUpdateAPIView(APIView):
    """
    PATCH: Быстрое обновление цены услуги
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        service = get_object_or_404(Service, pk=pk)
        new_price = request.data.get('price')
        
        if new_price is not None:
            try:
                service.price = int(new_price)
                service.save()
                return Response({'success': True, 'new_price': service.price})
            except ValueError:
                return Response({'error': 'Неверный формат цены'}, status=400)
                
        return Response({'error': 'Нет данных для обновления'}, status=400)