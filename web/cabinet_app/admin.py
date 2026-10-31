from django.contrib import admin
from django.utils.html import format_html
from .models import (
    CabinetUser,
    ClientRefreshToken,
    PasswordResetCode,
    ClientPushSubscription,
    NotificationLog,
    BonusTransaction,
    CashbackRule,
    Referral,
    AchievementDefinition,
    ClientAchievement,
    PersonalOffer,
)


@admin.register(CabinetUser)
class CabinetUserAdmin(admin.ModelAdmin):
    list_display = ('phone', 'client', 'is_active', 'is_blocked', 'referral_code', 'created_at')
    list_filter = ('is_active', 'is_blocked', 'consent_marketing', 'created_at')
    search_fields = ('phone', 'client__name', 'client__phone', 'referral_code')
    readonly_fields = ('password', 'last_login', 'last_login_ip', 'created_at', 'updated_at')
    raw_id_fields = ('client',)
    
    fieldsets = (
        ('Основное', {'fields': ('client', 'phone', 'password')}),
        ('Статус', {'fields': ('is_active', 'is_blocked', 'block_reason')}),
        ('Согласия', {'fields': ('consent_pd_at', 'consent_marketing', 'consent_marketing_at')}),
        ('Рефералка и входы', {'fields': ('referral_code', 'last_login', 'last_login_ip')}),
        ('Служебное', {'fields': ('created_at', 'updated_at')}),
    )

    def has_add_permission(self, request):
        # Лучше создавать пользователей через API регистрации, но если нужно вручную:
        return True


@admin.register(ClientRefreshToken)
class ClientRefreshTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'created_at', 'expires_at', 'revoked_at')
    list_filter = ('platform', 'revoked_at', 'created_at')
    search_fields = ('user__phone', 'user__client__name')
    readonly_fields = ('token_hash', 'user_agent', 'created_at', 'last_used_at')
    raw_id_fields = ('user',)


@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'created_at', 'expires_at', 'is_used', 'attempts')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__phone', 'code')
    readonly_fields = ('created_at',)
    raw_id_fields = ('user',)


@admin.register(ClientPushSubscription)
class ClientPushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'is_standalone', 'is_active', 'last_seen_at')
    list_filter = ('platform', 'is_standalone', 'is_active')
    search_fields = ('user__phone', 'user__client__name')
    readonly_fields = ('endpoint', 'p256dh', 'auth', 'user_agent', 'created_at', 'last_seen_at')
    raw_id_fields = ('user',)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'client', 'event_type', 'channel', 'status', 'sent_at')
    list_filter = ('channel', 'status', 'event_type', 'created_at')
    search_fields = ('client__phone', 'client__name', 'event_type')
    readonly_fields = ('created_at', 'sent_at', 'error', 'payload', 'subscription')
    raw_id_fields = ('client', 'booking')


@admin.register(BonusTransaction)
class BonusTransactionAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'client', 'amount', 'type', 'reason', 'balance_after', 'booking')
    list_filter = ('type', 'reason', 'created_at')
    search_fields = ('client__phone', 'client__name', 'description')
    readonly_fields = ('created_at', 'balance_after')
    raw_id_fields = ('client', 'booking', 'referral', 'created_by')
    
    def has_change_permission(self, request, obj=None):
        # Транзакции нельзя менять (только удалять или добавлять новые)
        return False


@admin.register(CashbackRule)
class CashbackRuleAdmin(admin.ModelAdmin):
    list_display = ('service', 'percent', 'valid_from', 'valid_until', 'is_active')
    list_filter = ('is_active', 'service', 'valid_from')
    search_fields = ('service__name',)
    date_hierarchy = 'valid_from'


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('referrer', 'referee', 'status', 'registered_at', 'rewarded_at')
    list_filter = ('status', 'registered_at')
    search_fields = ('referrer__phone', 'referrer__name', 'referee__phone', 'referee__name')
    readonly_fields = ('registered_at',)
    raw_id_fields = ('referrer', 'referee')


@admin.register(AchievementDefinition)
class AchievementDefinitionAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'rule_type', 'is_active', 'sort_order')
    list_filter = ('is_active', 'rule_type')
    search_fields = ('title', 'code')
    list_editable = ('is_active', 'sort_order')


@admin.register(ClientAchievement)
class ClientAchievementAdmin(admin.ModelAdmin):
    list_display = ('client', 'definition', 'unlocked_at', 'seen_by_client')
    list_filter = ('definition', 'seen_by_client', 'unlocked_at')
    search_fields = ('client__phone', 'client__name', 'definition__title')
    readonly_fields = ('unlocked_at',)
    raw_id_fields = ('client', 'definition')


@admin.register(PersonalOffer)
class PersonalOfferAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'is_active', 'valid_until', 'seen_at', 'used_at')
    list_filter = ('is_active', 'cta_type', 'created_at')
    search_fields = ('title', 'client__phone', 'client__name')
    raw_id_fields = ('client', 'created_by')
    readonly_fields = ('created_at', 'seen_at', 'used_at')
    
    fieldsets = (
        ('Основное', {'fields': ('client', 'title', 'body', 'image')}),
        ('Действие (CTA)', {'fields': ('cta_type', 'cta_payload')}),
        ('Статус', {'fields': ('is_active', 'valid_until', 'seen_at', 'used_at')}),
        ('Служебное', {'fields': ('created_at', 'created_by')}),
    )