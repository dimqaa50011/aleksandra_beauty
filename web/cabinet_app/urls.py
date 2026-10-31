from django.urls import path
from .apps import CabinetAppConfig

from .api.auth import (
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RefreshView,
    RegisterView,
)
from .api.bookings import (
    AppointmentDetailView,
    AppointmentListCreateView,
    AppointmentRescheduleView,
)
from .api.catalog import ServiceListView
from .api.slots import SlotListView
from .api.profile import AvatarUploadView, MeView, UpdateConsentsView
from .api.bonuses import BonusesView, CertificateDetailView, CertificatesView, ReferralView

app_name = CabinetAppConfig.name

urlpatterns = [
    # Auth
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/refresh/', RefreshView.as_view(), name='refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/password/reset-request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('auth/password/reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

    # Catalog & slots
    path('services/', ServiceListView.as_view(), name='services'),
    path('slots/', SlotListView.as_view(), name='slots'),

    # Appointments
    path('appointments/', AppointmentListCreateView.as_view(), name='appointments'),
    path('appointments/<int:pk>/', AppointmentDetailView.as_view(), name='appointment-detail'),
    path('appointments/<int:pk>/reschedule/', AppointmentRescheduleView.as_view(), name='appointment-reschedule'),
    path('me/', MeView.as_view(), name='me'),
    path('me/consents/', UpdateConsentsView.as_view(), name='me-consents'),
    path('bonuses/', BonusesView.as_view(), name='bonuses'),
    path('certificates/', CertificatesView.as_view(), name='certificates'),
    path('certificates/<int:pk>/', CertificateDetailView.as_view(), name='certificate-detail'),
    path('referral/', ReferralView.as_view(), name='referral'),
    path('me/avatar/', AvatarUploadView.as_view(), name='me-avatar'),
    
]