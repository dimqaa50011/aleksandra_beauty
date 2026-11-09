from rest_framework.response import Response
from rest_framework import status
from .base import CabinetAPIView
from ..models import Feedback
from ..serializers.feedback import FeedbackSerializer

class FeedbackListCreateView(CabinetAPIView):
    """GET: Список сообщений клиента. POST: Отправка нового сообщения."""
    
    def get(self, request):
        feedbacks = Feedback.objects.filter(client=request.user.client)
        return Response(FeedbackSerializer(feedbacks, many=True).data)

    def post(self, request):
        text = request.data.get('text', '').strip()
        
        if len(text) < 10:
            return Response(
                {'error': 'Сообщение должно содержать минимум 10 символов'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        Feedback.objects.create(
            client=request.user.client,
            text=text
        )
        return Response({'success': True, 'message': 'Сообщение отправлено'})