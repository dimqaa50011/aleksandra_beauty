from ninja.security import HttpBearer

from django.conf import settings
import jwt

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        try:
            decoded_payload = jwt.decode(token, settings.ADMIN_API_SECRET, algorithms=["HS256"])
            if decoded_payload["user"] in settings.WEB_PASSWORDS:
                return True
        except Exception as ex:
            ... # логровать и поднимать ошибку
    