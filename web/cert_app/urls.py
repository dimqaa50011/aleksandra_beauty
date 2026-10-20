from django.urls import path
from . import views, api

app_name = 'cert_app'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('list/', views.CertificateListView.as_view(), name='list'),
    path('add/', views.CertificateAddView.as_view(), name='add'),
    path('redeem/', views.CertificateRedeemView.as_view(), name='redeem'),
    path('redeem/select/', views.CertificateRedeemSelectView.as_view(), name='redeem_select'),
    path('<int:pk>/', views.CertificateDetailView.as_view(), name='detail'),
    path('<int:pk>/delete/', views.CertificateDeleteView.as_view(), name='delete'),
    path('<int:pk>/resend-email/', views.CertificateResendEmailView.as_view(), name='resend_email'),
    # path('api/app-certificates/', api.AdminCertificatesListAPIView.as_view(), name='api_app_certificates'),
    path('api/app-certificates/redeem/', api.AdminCertificateRedeemAPIView.as_view(), name='api_app_certificate_redeem'),
    path('api/app-certificates/create/', api.AdminCertificateCreateAPIView.as_view(), name='api_app_certificate_create'),
    path('api/app-certificates/', api.AdminCertificatesAPIView.as_view(), name='api_app_certificates'),
    path('api/app-certificates/<int:pk>/use/', api.AdminCertificateUseAPIView.as_view(), name='api_app_certificate_use'),
]