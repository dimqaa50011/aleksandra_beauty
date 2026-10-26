from django.http import HttpResponse
from django.urls import path
from django.views.generic import TemplateView
from . import views, api

app_name = 'beauty_app'

urlpatterns = [
    # Лендинги и каталог
    path('', views.LandingView.as_view(), name='landing'),
    path('lending/', views.Lend2View.as_view(), name='lending'),
    path('services/<int:category_id>/', views.category_services, name='category_services'),
    path('service/<int:service_id>/', views.service_detail, name='service_detail'),
    
    # Авторизация
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('access-denied/', views.AccessDeniedView.as_view(), name='access_denied'),
    
    # Общий дашборд (статистика и т.д.)
    path('admin-dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    path('api/app-services/', api.AdminServicesAPIView.as_view(), name='api_app_services'),
    path('api/app-services/<int:pk>/update/', api.AdminServiceUpdateAPIView.as_view(), name='api_app_service_update'),
    path('yandex_696a05861a1ca6ec.html', lambda request: HttpResponse("Verification: 696a05861a1ca6ec", content_type="text/html")),
]