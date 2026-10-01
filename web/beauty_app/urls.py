from django.urls import path
from . import views

app_name = 'beauty_app'

urlpatterns = [
    # Лендинги
    path('', views.LandingView.as_view(), name='landing'),
    path('lending/', views.Lend2View.as_view(), name='lending'),
    path('services/<int:category_id>/', views.category_services, name='category_services'),
    path('service/<int:service_id>/', views.service_detail, name='service_detail'),
    
    # Бронирование (публичное)
    path('booking/', views.booking_create, name='booking_create'),
    path('api/available-times/', views.get_available_times, name='available_times'),
    
    # Авторизация
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('access-denied/', views.AccessDeniedView.as_view(), name='access_denied'),
    
    # Админка (кастомная)
    path('admin-dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Управление блокировками
    path('admin-dashboard/blocked-slots/', views.BlockedSlotListView.as_view(), name='blocked_slots_list'),
    path('admin-dashboard/blocked-slots/add/', views.BlockedSlotAddView.as_view(), name='blocked_slot_add'),
    path('admin-dashboard/blocked-slots/<int:pk>/delete/', views.BlockedSlotDeleteView.as_view(), name='blocked_slot_delete'),
    
    # Ручное создание записи
    path('admin-dashboard/bookings/add/', views.AdminBookingCreateView.as_view(), name='admin_booking_create'),
]