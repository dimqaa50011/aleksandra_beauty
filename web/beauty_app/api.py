from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Service, ServiceCategory
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import PortfolioWork
from .serializers import PortfolioWorkSerializer

class AdminPortfolioListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request):
        works = PortfolioWork.objects.all().order_by('order')
        serializer = PortfolioWorkSerializer(works, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        serializer = PortfolioWorkSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

class AdminPortfolioDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, pk):
        try:
            work = PortfolioWork.objects.get(pk=pk)
            work.delete()
            return Response({'success': True})
        except PortfolioWork.DoesNotExist:
            return Response({'error': 'Не найдено'}, status=404)

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
                    'name': s.name,
                    'title': s.title,
                    'price': s.price,
                    'duration': s.duration,
                    'description': s.description,
                    'seo_description': s.seo_description,
                } for s in services]
            })
            
        return Response({'categories': data}, status=status.HTTP_200_OK)

class AdminServiceUpdateAPIView(APIView):
    """
    PATCH: Обновление любых полей услуги
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        service = get_object_or_404(Service, pk=pk)
        
        # Обновляем только те поля, которые пришли в запросе
        if 'title' in request.data:
            service.title = request.data['title']
        if 'name' in request.data:
            service.name = request.data['name']
        if 'price' in request.data:
            try:
                service.price = int(request.data['price'])
            except ValueError:
                return Response({'error': 'Неверный формат цены'}, status=400)
        if 'duration' in request.data:
            try:
                service.duration = int(request.data['duration'])
            except ValueError:
                return Response({'error': 'Неверный формат длительности'}, status=400)
        if 'description' in request.data:
            service.description = request.data['description']
        if 'seo_description' in request.data:
            service.seo_description = request.data['seo_description']
            
        service.save()
        
        return Response({
            'success': True, 
            'message': 'Услуга обновлена',
            'service': {
                'id': service.id,
                'title': service.title,
                'name': service.name,
                'price': service.price,
                'duration': service.duration,
                'description': service.description,
            }
        })