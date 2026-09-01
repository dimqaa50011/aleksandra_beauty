from django.urls import path, include
from . import views

app_name = 'beauty_app'

urlpatterns = [
    # Лендинги (доступны всем)
    path('', views.LandingView.as_view(), name='landing'),
    path('lending/', views.Lend2View.as_view(), name='lending'),
    
    # Авторизация
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('access-denied/', views.AccessDeniedView.as_view(), name='access_denied'),
    
    # Админка (только для админов)
    path('admin-dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    
]