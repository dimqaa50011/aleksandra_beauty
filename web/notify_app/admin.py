from django.contrib import admin
from .models import NotificationType, ClientNotificationSetting


@admin.register(NotificationType)
class NotificationTypeAdmin(admin.ModelAdmin):
    # Колонки, которые будут видны в общем списке
    list_display = (
        'name', 
        'code', 
        'category', 
        'allow_push', 
        'allow_sms', 
        'default_enabled', 
        'is_active'
    )
    
    # Фильтры справа
    list_filter = ('category', 'allow_push', 'allow_sms', 'is_active')
    
    # Поиск по этим полям
    search_fields = ('name', 'code', 'description')
    
    # Поля, которые можно менять прямо в списке (не заходя в карточку)
    list_editable = ('allow_push', 'allow_sms', 'is_active')
    
    # Группировка полей при редактировании
    fieldsets = (
        ('Основное', {
            'fields': ('code', 'name', 'description', 'category')
        }),
        ('Каналы доставки', {
            'fields': ('allow_push', 'allow_sms'),
            'description': 'Внимание: SMS стоит денег! Включайте только для важных уведомлений.'
        }),
        ('Статус', {
            'fields': ('default_enabled', 'is_active')
        }),
    )


@admin.register(ClientNotificationSetting)
class ClientNotificationSettingAdmin(admin.ModelAdmin):
    # Колонки в списке
    list_display = ('client', 'notification_type', 'is_enabled')
    
    # Фильтры
    list_filter = ('notification_type', 'is_enabled')
    
    # Поиск по имени или телефону клиента
    search_fields = ('client__name', 'client__phone')
    
    # Чтобы не грузить выпадающий список со всеми клиентами (если их тысячи),
    # используем поиск по ID (иконка лупы)
    raw_id_fields = ('client',)