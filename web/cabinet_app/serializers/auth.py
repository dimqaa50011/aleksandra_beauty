from rest_framework import serializers


class RegisterSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    name = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    email = serializers.EmailField(required=False, allow_blank=True, default='')
    consent_pd = serializers.BooleanField()
    consent_marketing = serializers.BooleanField(required=False, default=False)
    ref = serializers.CharField(max_length=12, required=False, allow_blank=True, default='')

    def validate_consent_pd(self, value):
        if not value:
            raise serializers.ValidationError('Требуется согласие на обработку персональных данных')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Пароли не совпадают'})
        return attrs


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)


class PasswordResetConfirmSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    code = serializers.CharField(min_length=6, max_length=6)
    new_password = serializers.CharField(min_length=8, write_only=True)