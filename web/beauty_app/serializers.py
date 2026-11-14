from rest_framework import serializers
from .models import PortfolioWork

class PortfolioWorkSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioWork
        fields = ['id', 'title', 'image_before', 'image_after', 'order', 'is_active']