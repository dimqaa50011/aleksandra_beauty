from django.contrib import admin
from .models import CertificateModel, CertificateNominal


@admin.register(CertificateNominal)
class CertificateNominalAdmin(admin.ModelAdmin):
    list_display = ('value', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    search_fields = ('value',)


@admin.register(CertificateModel)
class CertificateModelAdmin(admin.ModelAdmin):
    list_display = ('token', 'phone', 'email', 'price', 'expire_date', 'is_used', 'email_sended')
    list_filter = ('is_used', 'email_sended')
    search_fields = ('token', 'phone', 'email', 'client_name')
    readonly_fields = ('token', 'created_at', 'used_date')