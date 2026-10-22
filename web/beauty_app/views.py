from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import render, get_object_or_404, redirect

from .models import (
    AboutBlock,
    HeroSlide,
    MasterBlock,
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
# МИКСИН ДЛЯ ЗАЩИТЫ АДМИНКИ
# =============================================
class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy('beauty_app:login')
    permission_denied_message = 'Доступ запрещён. Требуются права администратора.'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return render(self.request, 'beauty_app/auth/access_denied.html', status=403)
        return redirect(self.login_url)


# =============================================
# ЛЕНДИНГИ (доступны всем)
# =============================================
class Lend2View(TemplateView):
    template_name = "beauty_app/lending.html"


# @method_decorator(cache_page(60 * 15), name='dispatch')
class LandingView(TemplateView):
    """Главная страница лендинга"""
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
        context['about'] = AboutBlock.objects.filter(is_active=True).first()
        context['master'] = MasterBlock.objects.filter(is_active=True).first()
        context['reviews'] = Review.objects.filter(is_active=True).order_by('-created_at')[:6]
        context['hero_slides'] = HeroSlide.objects.filter(is_active=True)
        return context


# =============================================
# СТРАНИЦЫ УСЛУГ (доступны всем)
# =============================================
def category_services(request, category_id):
    """Страница со списком услуг конкретной категории"""
    category = get_object_or_404(ServiceCategory, id=category_id, is_active=True)
    services = Service.objects.filter(
        category=category,
        is_active=True
    ).order_by('order', 'price')

    return render(request, 'beauty_app/category_services.html', {
        'category': category,
        'services': services,
    })


def service_detail(request, service_id):
    """Детальная страница конкретной услуги"""
    service = get_object_or_404(Service, id=service_id, is_active=True)
    related_services = Service.objects.filter(
        category=service.category,
        is_active=True
    ).exclude(id=service.id)[:3]

    return render(request, 'beauty_app/service_detail.html', {
        'service': service,
        'related_services': related_services,
    })


# =============================================
# АВТОРИЗАЦИЯ
# =============================================
class LoginView(AuthLoginView):
    template_name = 'beauty_app/auth/login.html'
    form_class = LoginForm
    redirect_authenticated_user = True
    success_url = reverse_lazy('beauty_app:dashboard')


class LogoutView(AuthLogoutView):
    next_page = reverse_lazy('beauty_app:login')


class AccessDeniedView(TemplateView):
    template_name = 'beauty_app/auth/access_denied.html'


# =============================================
# АДМИНКА (только для админов)
# =============================================
class DashboardView(AdminRequiredMixin, TemplateView):
    """Главная страница админки"""
    template_name = 'beauty_app/admin/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            from cert_app.controllers import CertController
            from django.conf import settings
            cert_controller = CertController(secret_key=settings.SECRET_KEY)
            stats = cert_controller.get_statistics()
            context['total'] = stats['total']
            context['active'] = stats['active']
            context['redeemed'] = stats['redeemed']
            context['expired'] = stats['expired']
            context['recent_certificates'] = cert_controller.get_all_certificates()[:5]
        except ImportError:
            context['total'] = 0
            context['active'] = 0
            context['redeemed'] = 0
            context['expired'] = 0
            context['recent_certificates'] = []
        return context