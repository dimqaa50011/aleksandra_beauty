from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from ..authentication import REFRESH_COOKIE_NAME, REFRESH_COOKIE_PATH
from ..serializers.auth import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
)
from ..services import auth as auth_service


REFRESH_TTL_SECONDS = 90 * 24 * 3600


def _client_ip(request) -> str | None:
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _platform(request) -> str:
    ua = request.META.get('HTTP_USER_AGENT', '').lower()
    if 'iphone' in ua or 'ipad' in ua:
        return 'ios'
    if 'android' in ua:
        return 'android'
    return 'desktop'


def _set_refresh_cookie(response: Response, raw: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw,
        max_age=REFRESH_TTL_SECONDS,
        httponly=True,
        secure=not settings.DEBUG,
        samesite='Lax',
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


def _user_payload(user) -> dict:
    return {
        'id': user.pk,
        'phone': user.phone,
        'display_phone': user.client.phone,
        'name': user.client.name,
        'email': user.client.email or '',
        'consent_marketing': user.consent_marketing,
        'referral_code': user.referral_code,
    }


def _auth_response(user, access: str, refresh_raw: str, *,
                   status_code: int = status.HTTP_200_OK) -> Response:
    resp = Response(
        {'access': access, 'user': _user_payload(user)},
        status=status_code,
    )
    _set_refresh_cookie(resp, refresh_raw)
    return resp


# ─────────────────────────────────────────────────────────────
# Регистрация
# ─────────────────────────────────────────────────────────────

class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'register'

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        user, access, refresh_raw = auth_service.register(
            phone=data['phone'],
            password=data['password'],
            name=data.get('name', ''),
            email=data.get('email', ''),
            consent_pd=data['consent_pd'],
            consent_marketing=data.get('consent_marketing', False),
            ref_code=data.get('ref', ''),
            ip=_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            platform=_platform(request),
        )
        return _auth_response(user, access, refresh_raw, status_code=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────
# Вход
# ─────────────────────────────────────────────────────────────

class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        user, access, refresh_raw = auth_service.login(
            phone=data['phone'],
            password=data['password'],
            ip=_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            platform=_platform(request),
        )
        return _auth_response(user, access, refresh_raw)


# ─────────────────────────────────────────────────────────────
# Refresh / Logout
# ─────────────────────────────────────────────────────────────

class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not raw:
            return Response(
                {'detail': 'No refresh token'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            user, access, new_raw = auth_service.refresh(
                raw,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                platform=_platform(request),
            )
        except AuthenticationFailed:
            resp = Response(
                {'detail': 'Invalid or expired refresh token'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            _clear_refresh_cookie(resp)
            return resp
        return _auth_response(user, access, new_raw)


class LogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if raw:
            auth_service.logout(raw)
        resp = Response({'detail': 'Выход выполнен'}, status=status.HTTP_200_OK)
        _clear_refresh_cookie(resp)
        return resp


# ─────────────────────────────────────────────────────────────
# Сброс пароля
# ─────────────────────────────────────────────────────────────

class PasswordResetRequestView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset_request'

    def post(self, request):
        ser = PasswordResetRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        auth_service.request_password_reset(
            ser.validated_data['phone'], ip=_client_ip(request),
        )
        return Response({
            'detail': 'Если аккаунт с таким телефоном существует, код отправлен по SMS',
        })


class PasswordResetConfirmView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset_confirm'

    def post(self, request):
        ser = PasswordResetConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        auth_service.confirm_password_reset(
            phone=data['phone'],
            code=data['code'],
            new_password=data['new_password'],
        )
        return Response({'detail': 'Пароль изменён. Войдите с новым паролем.'})