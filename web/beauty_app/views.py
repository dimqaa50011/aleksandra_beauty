from django.views.generic import TemplateView, FormView
from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.shortcuts import redirect, render
from django.contrib import messages
from django.urls import reverse_lazy
from django.conf import settings

from .models import (
    SiteSettings,
    HeroBlock,
    ServiceCategory,
    Service,
    Banner,
    TrustBlock,
    Review,
    MenuItem,
    FooterLink,
)
from .forms import LoginForm


# =============================================
# ЛЕНДИНГИ (доступны всем)
# =============================================
class Lend2View(TemplateView):
    template_name = "beauty_app/lending.html"


@method_decorator(cache_page(60 * 15), name='dispatch')
class LandingView(TemplateView):
    """
    Главная страница лендинга.
    Все данные подгружаются из базы через админку.
    """
    template_name = 'beauty_app/lending2.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['settings'] = SiteSettings.objects.first()
        context['hero'] = HeroBlock.objects.filter(is_active=True).first()
        context['categories'] = ServiceCategory.objects.filter(is_active=True)
        context['services'] = Service.objects.filter(is_active=True)
        context['banners'] = Banner.objects.filter(is_active=True)
        context['trust'] = TrustBlock.objects.filter(is_active=True).first()
        context['reviews'] = Review.objects.filter(is_active=True)
        context['menu_items'] = MenuItem.objects.filter(is_active=True)
        context['footer_links'] = FooterLink.objects.filter(is_active=True)

        return context


# =============================================
# АВТОРИЗАЦИЯ
# =============================================
class LoginView(AuthLoginView):
    """Страница входа"""
    template_name = 'beauty_app/auth/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True
    success_url = reverse_lazy('beauty_app:dashboard')


class LogoutView(AuthLogoutView):
    """Выход из системы"""
    next_page = reverse_lazy('beauty_app:login')


class AccessDeniedView(TemplateView):
    """Страница 403 — доступ запрещён"""
    template_name = 'beauty_app/auth/access_denied.html'


# =============================================
# МИКСИН ДЛЯ ЗАЩИТЫ АДМИНКИ
# =============================================
class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Миксин для проверки, что пользователь — администратор"""
    login_url = reverse_lazy('beauty_app:login')
    permission_denied_message = 'Доступ запрещён. Требуются права администратора.'
    
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return render(self.request, 'beauty_app/auth/access_denied.html', status=403)
        return redirect(self.login_url)


# =============================================
# АДМИНКА (только для админов)
# =============================================
class DashboardView(AdminRequiredMixin, TemplateView):
    """Главная страница админки"""
    template_name = 'beauty_app/admin/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем статистику через контроллер cert_app
        try:
            from cert_app.controllers import CertController
            cert_controller = CertController(secret_key=settings.SECRET_KEY)
            stats = cert_controller.get_statistics()
            context['total'] = stats['total']
            context['active'] = stats['active']
            context['redeemed'] = stats['redeemed']
            context['expired'] = stats['expired']
            context['recent_certificates'] = cert_controller.get_all_certificates()[:5]
        except ImportError:
            # Если cert_app не подключен — ставим заглушки
            context['total'] = 0
            context['active'] = 0
            context['redeemed'] = 0
            context['expired'] = 0
            context['recent_certificates'] = []
        
        return context