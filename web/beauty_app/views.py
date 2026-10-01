from django.views.generic import TemplateView, FormView, View
from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse_lazy
from django.conf import settings
from django.utils import timezone
from django import forms
from datetime import datetime, timedelta, time

from .models import (
    BlockedSlot,
    SiteSettings,
    HeroBlock,
    ServiceCategory,
    Service,
    Banner,
    TrustBlock,
    Review,
    MenuItem,
    FooterLink,
    Booking,
)
from .forms import AdminBookingForm, BlockedSlotForm, BookingForm, LoginForm


# =============================================
# ЛОГИКА ПРОВЕРКИ СВОБОДНЫХ СЛОТОВ
# =============================================
def is_time_slot_available(new_start_time, service, duration=None):
    """
    Проверяет, свободен ли слот (учитывает записи и заблокированные слоты).
    new_start_time: timezone-aware datetime
    """
    if duration is None:
        duration = getattr(service, 'duration', 60)

    new_end_time = new_start_time + timedelta(minutes=duration)

    # 1. Проверяем существующие записи
    day_start = new_start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    existing_bookings = Booking.objects.filter(
        appointment_datetime__gte=day_start,
        appointment_datetime__lt=day_end,
        status__in=['pending', 'confirmed']
    )

    for booking in existing_bookings:
        existing_start = booking.appointment_datetime
        existing_end = existing_start + timedelta(minutes=getattr(booking.service, 'duration', 60))

        if new_start_time < existing_end and new_end_time > existing_start:
            return False

    # 2. Проверяем заблокированные слоты
    target_date = new_start_time.date()
    blocked_slots = BlockedSlot.objects.filter(date=target_date)

    for slot in blocked_slots:
        slot_start = timezone.make_aware(
            datetime.combine(target_date, slot.start_time),
            timezone.get_current_timezone()
        )
        slot_end = timezone.make_aware(
            datetime.combine(target_date, slot.end_time),
            timezone.get_current_timezone()
        )

        if new_start_time < slot_end and new_end_time > slot_start:
            return False

    return True


# =============================================
# БРОНИРОВАНИЕ (доступно всем)
# =============================================
def booking_create(request):
    """Страница создания записи"""
    service_id = request.GET.get('service')
    initial_data = {}

    if service_id:
        try:
            service = Service.objects.get(id=service_id, is_active=True)
            initial_data['service'] = service
            initial_data['category'] = service.category
        except Service.DoesNotExist:
            pass

    if request.method == 'POST':
        form = BookingForm(request.POST, initial=initial_data)
        
        # Форма сама проверит дату, время и услугу на доступность!
        if form.is_valid():
            date_str = form.cleaned_data['appointment_date']
            time_str = form.cleaned_data['appointment_time']
            service = form.cleaned_data['service']
            
            # Собираем datetime (форма уже проверила, что он валидный и свободный)
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
            
            # Сохраняем
            booking = form.save(commit=False)
            booking.appointment_datetime = aware_dt
            booking.save()
            
            return redirect('beauty_app:booking_success') # Или куда тебе нужно
    else:
        form = BookingForm(initial=initial_data)

    return render(request, 'beauty_app/booking_form.html', {'form': form})

def get_available_times(request):
    """AJAX-эндпоинт для получения свободных слотов времени"""
    date_str = request.GET.get('date')
    service_id = request.GET.get('service_id')

    if not date_str or not service_id:
        return JsonResponse({'times': [], 'is_blocked': False, 'blocked_count': 0})

    try:
        service = Service.objects.get(id=service_id, is_active=True)
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except (Service.DoesNotExist, ValueError):
        return JsonResponse({'times': [], 'is_blocked': False, 'blocked_count': 0})

    # Длительность услуги в минутах
    duration = getattr(service, 'duration', 60)

    # Рабочие часы студии
    start_hour, end_hour = 9, 22

    available_times = []
    current_time = datetime.combine(target_date, time(start_hour, 0))
    end_time = datetime.combine(target_date, time(end_hour, 0))

    # Генерируем слоты с шагом 30 минут
    while current_time + timedelta(minutes=duration) <= end_time:
        aware_time = timezone.make_aware(current_time, timezone.get_current_timezone())
        
        # Проверяем, свободен ли слот (учитывает записи и блокировки)
        if is_time_slot_available(aware_time, service, duration):
            available_times.append(current_time.strftime("%H:%M"))

        current_time += timedelta(minutes=30)

    # Проверяем, есть ли полностью заблокированные дни
    full_day_blocked = BlockedSlot.objects.filter(
        date=target_date,
        start_time__lte=time(9, 0),
        end_time__gte=time(22, 0)
    ).exists()

    return JsonResponse({
        'times': available_times,
        'is_blocked': full_day_blocked,
        'blocked_count': BlockedSlot.objects.filter(date=target_date).count()
    })

# =============================================
# ФОРМЫ ДЛЯ АДМИНКИ
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
# УПРАВЛЕНИЕ ЗАБЛОКИРОВАННЫМИ СЛОТАМИ (только для админов)
# =============================================
class BlockedSlotListView(AdminRequiredMixin, TemplateView):
    """Список заблокированных слотов"""
    template_name = 'beauty_app/admin/blocked_slots_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['blocked_slots'] = BlockedSlot.objects.all()
        return context


class BlockedSlotAddView(AdminRequiredMixin, FormView):
    """Добавление заблокированного слота"""
    template_name = 'beauty_app/admin/blocked_slot_form.html'
    form_class = BlockedSlotForm
    success_url = reverse_lazy('beauty_app:blocked_slots_list')

    def form_valid(self, form):
        BlockedSlot.objects.create(
            date=form.cleaned_data['date'],
            start_time=form.cleaned_data['start_time'],
            end_time=form.cleaned_data['end_time'],
            slot_type=form.cleaned_data['slot_type'],
            reason=form.cleaned_data.get('reason', '')
        )
        messages.success(self.request, 'Временной слот заблокирован')
        return super().form_valid(form)


class BlockedSlotDeleteView(AdminRequiredMixin, View):
    """Удаление заблокированного слота"""

    def post(self, request, pk):
        slot = get_object_or_404(BlockedSlot, pk=pk)
        slot.delete()
        messages.success(request, 'Заблокированный слот удален')
        return redirect('beauty_app:blocked_slots_list')


# =============================================
# РУЧНОЕ СОЗДАНИЕ ЗАПИСИ АДМИНОМ
# =============================================
class AdminBookingCreateView(AdminRequiredMixin, FormView):
    """Ручное создание записи администратором"""
    template_name = 'beauty_app/admin/booking_form.html'
    form_class = AdminBookingForm
    success_url = reverse_lazy('beauty_app:bookings_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        service_id = self.request.GET.get('service')
        if service_id:
            try:
                service = Service.objects.get(id=service_id, is_active=True)
                form.initial['service'] = service
                form.initial['category'] = service.category
            except Service.DoesNotExist:
                pass
        return form

    def form_valid(self, form):
        date_str = self.request.POST.get('appointment_date')
        time_str = self.request.POST.get('appointment_time')

        if date_str and time_str:
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())

            if is_time_slot_available(aware_dt, form.cleaned_data['service']):
                booking = form.save(commit=False)
                booking.appointment_datetime = aware_dt
                booking.status = form.cleaned_data['status']
                booking.save()
                messages.success(self.request, f'Запись для {booking.client_name} создана')
                return redirect('beauty_app:bookings_list')
            else:
                messages.error(self.request, 'Это время уже занято или заблокировано.')
                return self.form_invalid(form)

        return self.form_invalid(form)


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
# ЛЕНДИНГИ (доступны всем)
# =============================================
class Lend2View(TemplateView):
    template_name = "beauty_app/lending.html"


@method_decorator(cache_page(60 * 15), name='dispatch')
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
        return context


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
# МИКСИН ДЛЯ ЗАЩИТЫ АДМИНКИ
# =============================================

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