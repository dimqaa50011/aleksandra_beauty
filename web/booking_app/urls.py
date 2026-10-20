from django.urls import path
from . import views
from . import api

app_name = 'booking_app'

urlpatterns = [
    # ==========================================
    # ПУБЛИЧНЫЕ СТРАНИЦЫ БРОНИРОВАНИЯ
    # ==========================================
    path('booking/', views.booking_create, name='booking_create'),
    path('booking/success/', views.booking_success, name='booking_success'),
    
    # ==========================================
    # API ЭНДПОИНТЫ (AJAX)
    # ==========================================
    # Проверка свободных слотов
    path('api/available-times/', views.get_available_times, name='available_times'),
    
    # Умная проверка email (новый клиент или нет)
    path('api/check-email/', views.check_email_view, name='check_email'),
    
    # Отправка и проверка кода подтверждения
    path('api/send-email-code/', views.send_email_code_view, name='send_email_code'),
    path('api/verify-email-code/', views.verify_email_code_view, name='verify_email_code'),
    path('api/free-slots/', views.get_free_slots_for_admin, name='free_slots'),
    path('api/create-booking/', views.api_create_booking, name='api_create_booking'),
    path('api/services-by-category/', views.get_services_by_category, name='api_services_by_category'),
    path('api/save-push-subscription/', views.save_push_subscription, name='save_push_subscription'),
    path('api/app-login/', views.app_login, name='app_login'),
    path('api/app-register-fcm/', views.app_register_fcm_token, name='app_register_fcm'),
    path('api/app-notifications/', views.app_notifications, name='app_notifications'),
    path('vk-app/', views.vk_booking_view, name='vk_booking'),
    path('telegram/', views.telegram_booking_view, name='telegram_booking'),
    path('max/', views.max_booking_view, name='max_booking'),
    
    # ==========================================
    # АДМИНКА: УПРАВЛЕНИЕ ЗАПИСЯМИ
    # ==========================================
    path('admin-dashboard/schedule/', views.BookingsScheduleView.as_view(), name='bookings_schedule'),
    path('admin-dashboard/bookings/', views.BookingsListView.as_view(), name='bookings_list'),
    path('admin-dashboard/bookings/add/', views.AdminBookingCreateView.as_view(), name='admin_booking_create'),
    path('admin-dashboard/bookings/<int:pk>/confirm/', views.BookingConfirmView.as_view(), name='booking_confirm'),
    path('admin-dashboard/bookings/<int:pk>/cancel/', views.BookingCancelView.as_view(), name='booking_cancel'),
    path('admin-dashboard/bookings/<int:pk>/edit/', views.booking_edit, name='booking_edit'),
    
    # ==========================================
    # АДМИНКА: УПРАВЛЕНИЕ СЛОТАМИ
    # ==========================================
    path('admin-dashboard/blocked-slots/', views.BlockedSlotListView.as_view(), name='blocked_slots_list'),
    path('admin-dashboard/blocked-slots/add/', views.BlockedSlotAddView.as_view(), name='blocked_slot_add'),
    path('admin-dashboard/blocked-slots/<int:pk>/delete/', views.BlockedSlotDeleteView.as_view(), name='blocked_slot_delete'),
    
    
    
    
    
    
    path('api/app-bookings/', api.AdminBookingsListAPIView.as_view(), name='api_app_bookings'),
    path('api/app-bookings/<int:pk>/status/', api.AdminBookingStatusAPIView.as_view(), name='api_app_booking_status'),
    path('api/app-block-day/', api.AdminBlockDayAPIView.as_view(), name='api_app_block_day'),
    path('api/app-services/', api.ServiceListAPIView.as_view(), name='api_app_services'),
    path('api/app-blocked-slots/', api.AdminBlockedSlotsAPIView.as_view(), name='api_app_blocked_slots'),
    path('api/app-blocked-slots/<int:pk>/', api.AdminBlockedSlotDeleteAPIView.as_view(), name='api_app_blocked_slot_delete'),
    path('api/app-calendar/', api.AdminCalendarAPIView.as_view(), name='api_app_calendar'),
    path('api/app-clients/', api.AdminClientsAPIView.as_view(), name='api_app_clients'),
    path('api/admin-available-times/', views.get_admin_available_times, name='admin_available_times'),
]