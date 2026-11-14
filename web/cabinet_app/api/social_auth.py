from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from ..models import CabinetUser, ClientRefreshToken
from ..authentication import issue_access_token
from ..services.social_auth import validate_telegram_data, validate_max_data, validate_vk_data
from .auth import _auth_response, _client_ip, _platform

class SocialAuthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, platform):
        data = request.data
        user_data = None

        try:
            if platform == 'telegram':
                user_data = validate_telegram_data(data.get('init_data', ''))
                platform_id = str(user_data['id'])
                lookup = {'telegram_id': platform_id}
            elif platform == 'max':
                user_data = validate_max_data(data.get('init_data', ''))
                platform_id = str(user_data['id'])
                lookup = {'max_id': platform_id}
            elif platform == 'vk':
                user_data = validate_vk_data(data.get('launch_params', {}))
                platform_id = str(user_data['id'])
                lookup = {'vk_id': platform_id}
            else:
                return Response({'error': 'Unknown platform'}, status=400)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Ищем или создаем пользователя
        user = CabinetUser.objects.filter(**lookup).first()
        is_new = False

        if not user:
            is_new = True
            user = CabinetUser(**lookup)
            user.set_unusable_password() # Пароля пока нет!
            
            # Пытаемся взять имя из соцсети
            
            user.save()

        # Выдаем токены
        access = issue_access_token(user)
        _, refresh_raw = ClientRefreshToken.issue(user, user_agent=request.META.get('HTTP_USER_AGENT', ''), platform=platform)

        resp = _auth_response(user, access, refresh_raw)
        resp.data['is_new'] = is_new
        return resp