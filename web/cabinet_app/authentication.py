import jwt
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import authentication, exceptions

from .models import CabinetUser


ACCESS_TTL_MINUTES = 15
REFRESH_COOKIE_NAME = 'cabinet_refresh'
REFRESH_COOKIE_PATH = '/api/client/cabinet/v1/auth/'


def issue_access_token(user: CabinetUser) -> str:
    now = timezone.now()
    payload = {
        'sub': str(user.pk),
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(minutes=ACCESS_TTL_MINUTES)).timestamp()),
        'typ': 'access',
        'scope': 'cabinet',
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')


def decode_access_token(raw: str) -> dict:
    return jwt.decode(raw, settings.SECRET_KEY, algorithms=['HS256'])


class CabinetJWTAuthentication(authentication.BaseAuthentication):
    """Bearer access-токен кабинета. request.user = CabinetUser."""

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()
        if not header or header[0].lower() != b'bearer':
            return None
        if len(header) != 2:
            raise exceptions.AuthenticationFailed('Invalid Authorization header')

        try:
            payload = decode_access_token(header[1])
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token expired')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid token')

        if payload.get('scope') != 'cabinet':
            raise exceptions.AuthenticationFailed('Wrong token scope')

        user = CabinetUser.objects.select_related('client').filter(
            pk=payload.get('sub'), is_active=True, is_blocked=False,
        ).first()
        if user is None:
            raise exceptions.AuthenticationFailed('User not found or blocked')

        return (user, payload)

    def authenticate_header(self, request):
        return 'Bearer'