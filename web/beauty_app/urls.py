from django.urls import path, include
from . import views

app_name = 'beauty_app'

urlpatterns = [
    # Лендинги (доступны всем)
    path('', views.LandingView.as_view(), name='landing'),
    path('lending/', views.Lend2View.as_view(), name='lending'),
    path('services/<int:category_id>/', views.category_services, name='category_services'),
    path('service/<int:service_id>/', views.service_detail, name='service_detail'),
    
    # Авторизация
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('access-denied/', views.AccessDeniedView.as_view(), name='access_denied'),
    
    # Админка (только для админов)
    path('admin-dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    
]