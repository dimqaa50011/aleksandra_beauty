from django.urls import path
from .views import AdminNotificationTypeListCreateView, AdminNotificationTypeDetailView

urlpatterns = [
    path('types/', AdminNotificationTypeListCreateView.as_view(), name='admin-notification-types'),
    path('types/<int:pk>/', AdminNotificationTypeDetailView.as_view(), name='admin-notification-type-detail'),
]