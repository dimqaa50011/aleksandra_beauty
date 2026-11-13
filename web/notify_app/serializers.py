from rest_framework import serializers
from .models import NotificationType

class NotificationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationType
        fields = [
            'id', 'code', 'name', 'description', 'category', 
            'allow_push', 'allow_sms', 'default_enabled', 'is_active'
        ]