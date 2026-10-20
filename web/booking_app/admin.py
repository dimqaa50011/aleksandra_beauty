from django.contrib import admin
from .models import APIToken, Client, EmailVerificationCode, Booking, DayOff, BlockedSlot, PushSubscription, SMSTemplate


@admin.register(SMSTemplate)
class SMSTemplateAdmin(admin.ModelAdmin):
    pass


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    pass
# =============================================
# APIToken
# =============================================
@admin.register(APIToken)
class APITokenAdmin(admin.ModelAdmin):
    list_display = ('name', 'token_preview', 'is_active', 'created_at', 'last_used')
    list_filter = ('is_active',)
    search_fields = ('name',)
    readonly_fields = ('token', 'created_at', 'last_used')

    def token_preview(self, obj):
        """Показываем только первые 16 символов токена"""
        return f"{obj.token[:16]}..."
    token_preview.short_description = 'Токен'


# =============================================
# Client (CRM)
# =============================================
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_verified', 'total_bookings', 'first_visit', 'last_visit')
    list_filter = ('is_verified',)
    search_fields = ('email',)
    readonly_fields = ('first_visit', 'last_visit')


# =============================================
# EmailVerificationCode
# =============================================
@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('email', 'code', 'is_used', 'attempts', 'created_at', 'is_expired_display')
    list_filter = ('is_used',)
    search_fields = ('email', 'code')
    readonly_fields = ('created_at',)

    def is_expired_display(self, obj):
        """Показываем, истек ли код"""
        if obj.is_expired:
            return '✅ Да'
        return '❌ Нет'
    is_expired_display.short_description = 'Истек'


# =============================================
# Booking (Записи)
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('client_name', 'phone', 'get_services_list', 'appointment_datetime', 'status')
    list_filter = ('status', 'appointment_datetime')  # <-- Убрали 'service'
    search_fields = ('client_name', 'phone', 'email')
    readonly_fields = ('created_at', 'updated_at', 'google_event_id')
    date_hierarchy = 'appointment_datetime'
    filter_horizontal = ('services',)  # <-- Удобный выбор нескольких услуг

    def get_services_list(self, obj):
        """Возвращает список услуг через запятую"""
        return ", ".join([s.name for s in obj.services.all()])
    get_services_list.short_description = 'Услуги'

    fieldsets = (
        ('Клиент', {
            'fields': ('client_name', 'phone', 'email')
        }),
        ('Запись', {
            'fields': ('services', 'appointment_datetime', 'status')  # <-- Заменили service на services
        }),
        ('Системное', {
            'fields': ('google_event_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# =============================================
# DayOff (Выходные дни)
# =============================================
@admin.register(DayOff)
class DayOffAdmin(admin.ModelAdmin):
    list_display = ('date', 'reason', 'created_at')
    search_fields = ('reason',)
    date_hierarchy = 'date'


# =============================================
# BlockedSlot (Заблокированные слоты)
# =============================================
@admin.register(BlockedSlot)
class BlockedSlotAdmin(admin.ModelAdmin):
    list_display = ('date', 'is_full_day', 'start_time', 'end_time', 'slot_type', 'reason')
    list_filter = ('slot_type', 'is_full_day', 'date')
    search_fields = ('reason',)
    date_hierarchy = 'date'

    fieldsets = (
        ('Основное', {
            'fields': ('date', 'is_full_day')
        }),
        ('Время (если не на весь день)', {
            'fields': ('start_time', 'end_time'),
            'description': 'Оставьте пустым, если выбрано "На весь день"'
        }),
        ('Детали', {
            'fields': ('slot_type', 'reason')
        }),
    )