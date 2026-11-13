from django.urls import path

from notify_app.api import NotificationSettingsView
from .views import AdminNotificationTypeListCreateView, AdminNotificationTypeDetailView

urlpatterns = [
    path('types/', AdminNotificationTypeListCreateView.as_view(), name='admin-notification-types'),
    path('types/<int:pk>/', AdminNotificationTypeDetailView.as_view(), name='admin-notification-type-detail'),
    path('notification-settings/', NotificationSettingsView.as_view(), name='notification-settings'),
]