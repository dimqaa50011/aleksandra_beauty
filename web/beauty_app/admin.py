from django.contrib import admin
from . import models


@admin.register(models.SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'phone', 'email')
    fieldsets = (
        ('Основное', {'fields': ('site_name', 'site_logo')}),
        ('Контакты', {'fields': ('phone', 'whatsapp', 'telegram', 'email')}),
        ('Адрес', {'fields': ('address', 'map_iframe')}),
        ('SEO', {'fields': ('meta_title', 'meta_description')}),
        ('Соцсети', {'fields': ('instagram', 'vk')}),
        ('Футер', {'fields': ('footer_text',)}),
    )


@admin.register(models.HeroBlock)
class HeroBlockAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active')


@admin.register(models.ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'order', 'is_active')
    list_editable = ('order', 'is_active')


@admin.register(models.Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'old_price', 'is_bestseller', 'is_active', 'order')
    list_editable = ('price', 'old_price', 'is_bestseller', 'is_active', 'order')
    list_filter = ('category', 'is_active', 'is_bestseller')
    search_fields = ('name',)


@admin.register(models.Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'order')


@admin.register(models.TrustBlock)
class TrustBlockAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active')


@admin.register(models.Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('client_name', 'rating', 'is_active', 'created_at')
    list_editable = ('rating', 'is_active')
    search_fields = ('client_name', 'text')


@admin.register(models.MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'order', 'is_active')
    list_editable = ('order', 'is_active')


@admin.register(models.FooterLink)
class FooterLinkAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'order', 'is_active')
    list_editable = ('order', 'is_active')