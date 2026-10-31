from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from ..authentication import CabinetJWTAuthentication


class CabinetAPIView(APIView):
    """Базовый класс для защищённых вьюх кабинета. request.user = CabinetUser."""
    authentication_classes = [CabinetJWTAuthentication]
    permission_classes = [IsAuthenticated]