from django.urls import path
from .apps import StatsAppConfig
from . import api

app_name = StatsAppConfig.name


urlpatterns = [
    path('api/app-stats/', api.AdminStatsAPIView.as_view(), name='api_app_stats'),
    path('api/app-expenses/', api.AdminExpenseAPIView.as_view(), name='api_app_expenses'),
]