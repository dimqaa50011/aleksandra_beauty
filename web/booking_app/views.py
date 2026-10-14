from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, TemplateView, FormView, View
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta, time as dt_time
import json

from .models import Booking, BlockedSlot, DayOff, EmailVerificationCode, Client, PushSubscription
from .forms import BookingForm, AdminBookingForm, BlockedSlotForm
from beauty_app.models import Service, ServiceCategory

try:
    from pywebpush import webpush, WebPushException
    HAS_WEBPUSH = True
except ImportError:
    HAS_WEBPUSH = False


def send_push_notification(title, body, url=None):
    """Отправляет пуш всем админам"""
    if not HAS_WEBPUSH:
        print("⚠️ pywebpush не установлен")
        return
    
    subscriptions = PushSubscription.objects.all()
    if not subscriptions.exists():
        print("Нет подписок на пуши")
        return
    
    vapid_private_key = getattr(settings, 'VAPID_PRIVATE_KEY', '')
    vapid_claims = {
        'sub': f'mailto:{getattr(settings, "VAPID_ADMIN_EMAIL", "admin@example.com")}',
    }
    
    payload = json.dumps({
        'title': title,
        'body': body,
        'url': url or '/admin-dashboard/bookings/',
    })
    
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    'endpoint': sub.endpoint,
                    'keys': {
                        'p256dh': sub.p256dh,
                        'auth': sub.auth,
                    }
                },
                data=payload,
                vapid_private_key=vapid_private_key,
                vapid_claims=vapid_claims,
            )
            print(f"✅ Пуш отправлен пользователю {sub.user.username}")
        except WebPushException as e:
            print(f"❌ Ошибка отправки пуша: {e}")
            if e.response and e.response.status_code in [404, 410]:
                sub.delete()
                print(f"🗑️ Удалена невалидная подписка {sub.user.username}")


@csrf_exempt
@require_POST
def save_push_subscription(request):
    """Сохраняет подписку на пуши от фронтенда"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Не авторизован'}, status=401)
    
    try:
        data = json.loads(request.body)
        subscription = data['subscription']
        
        PushSubscription.objects.update_or_create(
            user=request.user,
            endpoint=subscription['endpoint'],
            defaults={
                'p256dh': subscription['keys']['p256dh'],
                'auth': subscription['keys']['auth'],
            }
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def booking_edit(request, pk):
    """Редактирование записи администратором"""
    booking = get_object_or_404(Booking, pk=pk)
    
    if request.method == 'POST':
        form = AdminBookingForm(request.POST, instance=booking)
        
        if form.is_valid():
            date_str = form.cleaned_data['appointment_date']
            time_str = form.cleaned_data['appointment_time']
            
            # Получаем услуги из скрытого поля services_ids или из формы
            services_ids_str = request.POST.get('services_ids', '')
            if services_ids_str:
                services_ids = [int(id) for id in services_ids_str.split(',') if id]
                services = Service.objects.filter(id__in=services_ids, is_active=True)
            else:
                services = form.cleaned_data.get('services', booking.services.all())
            
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
            
            # Считаем общую длительность
            duration = sum(s.duration for s in services if s.duration)
            new_end_time = aware_dt + timedelta(minutes=duration)
            
            # Проверяем конфликты (исключая саму редактируемую запись)
            conflicting = Booking.objects.filter(
                appointment_datetime__date=aware_dt.date(),
                status__in=['pending', 'confirmed']
            ).exclude(pk=booking.pk).prefetch_related('services')
            
            is_available = True
            for b in conflicting:
                b_duration = sum(s.duration for s in b.services.all() if s.duration)
                b_start = b.appointment_datetime
                b_end = b_start + timedelta(minutes=b_duration)
                if aware_dt < b_end and new_end_time > b_start:
                    is_available = False
                    break
            
            if not is_available:
                form.add_error('appointment_time', 'Это время уже занято другой записью.')
                return render(request, 'booking_app/admin/booking_edit.html', {
                    'form': form,
                    'booking': booking
                })
            
            # Сохраняем изменения
            booking = form.save(commit=False)
            booking.appointment_datetime = aware_dt
            booking.save()
            booking.services.set(services) # <-- Сохраняем M2M связи
            
            # Обновляем Google Calendar (если функция существует)
            try:
                from .google_calendar import create_or_update_google_event
                event_id = create_or_update_google_event(booking)
                if event_id:
                    booking.google_event_id = event_id
                    booking.save(update_fields=['google_event_id'])
            except Exception as e:
                print(f"Ошибка обновления Google Calendar: {e}")
            
            messages.success(request, f'Запись для {booking.client_name} обновлена')
            return redirect('booking_app:bookings_list')
    else:
        initial_data = {
            'appointment_date': booking.appointment_datetime.date(),
            'appointment_time': booking.appointment_datetime.strftime('%H:%M'),
        }
        form = AdminBookingForm(instance=booking, initial=initial_data)
    
    return render(request, 'booking_app/admin/booking_edit.html', {
        'form': form,
        'booking': booking
    })


def get_services_by_category(request):
    """Возвращает список услуг конкретной категории в формате JSON"""
    category_id = request.GET.get('category_id')
    
    if not category_id:
        return JsonResponse({'services': []})
    
    try:
        services = Service.objects.filter(
            category_id=category_id, 
            is_active=True
        ).values('id', 'name', 'price', 'duration') # <-- Добавили duration для фронтенда
        
        return JsonResponse({'services': list(services)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def vk_booking_view(request):
    """Страница записи для VK Mini App"""
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            date_str = form.cleaned_data['appointment_date']
            time_str = form.cleaned_data['appointment_time']
            email = form.cleaned_data['email']
            
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
            
            booking = form.save(commit=False)
            booking.appointment_datetime = aware_dt
            booking.save()
            
            # === СОХРАНЕНИЕ НЕСКОЛЬКИХ УСЛУГ ===
            services_ids_str = request.POST.get('services_ids', '')
            if services_ids_str:
                services_ids = [int(id) for id in services_ids_str.split(',') if id]
                services = Service.objects.filter(id__in=services_ids, is_active=True)
                booking.services.set(services)
            
            services_names = ", ".join([s.name for s in booking.services.all()])
            
            # Обновляем CRM
            if email:
                client, created = Client.objects.get_or_create(email=email)
                client.total_bookings += 1
                client.is_verified = True
                client.save()
                
                try:
                    send_mail(
                        subject='🌸 Ваша запись в Sasha Sugar подтверждена!',
                        message=f"Здравствуйте, {booking.client_name}!\n\nВаша запись на {date_str} в {time_str} ({services_names}) успешно оформлена.\n\nЖдем вас по адресу: Спасский переулок, 7",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                except Exception:
                    pass

            return render(request, 'booking_app/vk_success.html', {'booking': booking})
    else:
        form = BookingForm()
    
    return render(request, 'booking_app/vk_booking.html', {'form': form})

def telegram_booking_view(request):
    """Страница записи для Telegram Mini App"""
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            date_str = form.cleaned_data['appointment_date']
            time_str = form.cleaned_data['appointment_time']
            email = form.cleaned_data['email']
            
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
            
            booking = form.save(commit=False)
            booking.appointment_datetime = aware_dt
            booking.save()
            
            # Сохранение нескольких услуг
            services_ids_str = request.POST.get('services_ids', '')
            if services_ids_str:
                services_ids = [int(id) for id in services_ids_str.split(',') if id]
                services = Service.objects.filter(id__in=services_ids, is_active=True)
                booking.services.set(services)
            
            services_names = ", ".join([s.name for s in booking.services.all()])
            
            # Обновляем CRM
            if email:
                client, created = Client.objects.get_or_create(email=email)
                client.total_bookings += 1
                client.is_verified = True
                client.save()
                
                try:
                    send_mail(
                        subject=' Ваша запись в Sasha Sugar подтверждена!',
                        message=f"Здравствуйте, {booking.client_name}!\n\nВаша запись на {date_str} в {time_str} ({services_names}) успешно оформлена.\n\nЖдем вас по адресу: Спасский переулок, 7",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                except Exception:
                    pass

            return render(request, 'booking_app/telegram_success.html', {'booking': booking})
    else:
        form = BookingForm()
    
    return render(request, 'booking_app/telegram_booking.html', {'form': form})


def max_booking_view(request):
    """Страница записи для MAX Mini App"""
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            date_str = form.cleaned_data['appointment_date']
            time_str = form.cleaned_data['appointment_time']
            email = form.cleaned_data['email']
            
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
            
            booking = form.save(commit=False)
            booking.appointment_datetime = aware_dt
            booking.save()
            
            # Сохранение нескольких услуг
            services_ids_str = request.POST.get('services_ids', '')
            if services_ids_str:
                services_ids = [int(id) for id in services_ids_str.split(',') if id]
                services = Service.objects.filter(id__in=services_ids, is_active=True)
                booking.services.set(services)
            
            services_names = ", ".join([s.name for s in booking.services.all()])
            
            # Обновляем CRM
            if email:
                client, created = Client.objects.get_or_create(email=email)
                client.total_bookings += 1
                client.is_verified = True
                client.save()
                
                try:
                    send_mail(
                        subject='🌸 Ваша запись в Sasha Sugar подтверждена!',
                        message=f"Здравствуйте, {booking.client_name}!\n\nВаша запись на {date_str} в {time_str} ({services_names}) успешно оформлена.\n\nЖдем вас по адресу: Спасский переулок, 7",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                except Exception:
                    pass

            return render(request, 'booking_app/max_success.html', {'booking': booking})
    else:
        form = BookingForm()
    
    return render(request, 'booking_app/max_booking.html', {'form': form})

@csrf_exempt
@require_POST
def api_create_booking(request):
    """Защищённый API endpoint для создания записи"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат JSON'}, status=400)

    client_name = data.get('client_name', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    date_str = data.get('date')
    time_str = data.get('time')
    
    # Поддержка и services_ids (новое), и service_id (старое, для совместимости)
    services_ids_input = data.get('services_ids') or data.get('service_id')

    if not client_name or not phone or not services_ids_input or not date_str or not time_str:
        return JsonResponse({'error': 'Не заполнены обязательные поля'}, status=400)

    try:
        services_ids = [int(id) for id in str(services_ids_input).split(',') if id]
        services = Service.objects.filter(id__in=services_ids, is_active=True)
        if not services.exists():
            return JsonResponse({'error': 'Услуги не найдены'}, status=404)
    except ValueError:
        return JsonResponse({'error': 'Неверный формат ID услуг'}, status=400)

    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        time = datetime.strptime(time_str, '%H:%M').time()
        appointment_datetime = timezone.make_aware(
            datetime.combine(date, time),
            timezone.get_current_timezone()
        )
    except ValueError:
        return JsonResponse({'error': 'Неверный формат даты или времени'}, status=400)

    total_duration = sum(s.duration for s in services if s.duration)

    if not is_time_slot_available(appointment_datetime, services=services, duration=total_duration):
        return JsonResponse({'error': 'Это время уже занято или заблокировано'}, status=409)

    booking = Booking.objects.create(
        client_name=client_name,
        phone=phone,
        email=email if email else None,
        appointment_datetime=appointment_datetime,
        status='confirmed'
    )
    booking.services.set(services) # <-- Сохраняем M2M

    if email:
        client, created = Client.objects.get_or_create(email=email)
        client.total_bookings += 1
        client.is_verified = True
        client.save()

        try:
            services_names = ", ".join([s.name for s in services])
            send_mail(
                subject='🌸 Ваша запись в Sasha Sugar подтверждена!',
                message=f"Здравствуйте, {client_name}!\n\nВаша запись успешно оформлена.\n\n📅 Дата: {date_str}\n⏰ Время: {time_str}\n💅 Услуги: {services_names}\n📍 Адрес: Санкт-Петербург, Спасский переулок, 7",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Ошибка отправки письма: {e}")

    return JsonResponse({
        'success': True,
        'booking_id': booking.id,
        'message': 'Запись успешно создана',
        'booking_details': {
            'client_name': booking.client_name,
            'services': [s.name for s in services],
            'date': booking.appointment_datetime.strftime('%Y-%m-%d'),
            'time': booking.appointment_datetime.strftime('%H:%M'),
            'status': booking.get_status_display()
        }
    }, status=201)


# =============================================
# МИКСИН ДЛЯ АДМИНКИ
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
# ЛОГИКА ПРОВЕРКИ СВОБОДНЫХ СЛОТОВ
# =============================================
def is_time_slot_available(new_start_time, services=None, duration=None):
    """Проверяет, свободен ли слот (учитывает записи и заблокированные слоты)."""
    if duration is None and services:
        duration = sum(s.duration for s in services if s.duration)
    elif duration is None:
        duration = 60 # fallback

    new_end_time = new_start_time + timedelta(minutes=duration)
    target_date = new_start_time.date()
    current_tz = timezone.get_current_timezone()

    # 1. Проверяем заблокированные слоты
    blocked_slots = BlockedSlot.objects.filter(date=target_date)
    for slot in blocked_slots:
        if slot.is_full_day:
            return False
        
        if slot.start_time and slot.end_time:
            slot_start = timezone.make_aware(datetime.combine(target_date, slot.start_time), current_tz)
            slot_end = timezone.make_aware(datetime.combine(target_date, slot.end_time), current_tz)

            if new_start_time < slot_end and new_end_time > slot_start:
                return False    

    # 2. Проверяем существующие записи
    existing_bookings = Booking.objects.filter(
        appointment_datetime__date=target_date,
        status__in=['pending', 'confirmed']
    ).prefetch_related('services')

    for booking in existing_bookings:
        booking_duration = sum(s.duration for s in booking.services.all() if s.duration)
        booking_start = booking.appointment_datetime
        booking_end = booking_start + timedelta(minutes=booking_duration)

        if new_start_time < booking_end and new_end_time > booking_start:
            return False

    return True


def get_free_slots_for_admin(request):
    """API для админки: возвращает свободные слоты и информацию о записях"""
    date_str = request.GET.get('date')
    if not date_str:
        return JsonResponse({'error': 'Не указана дата'}, status=400)
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Неверный формат даты'}, status=400)
    
    WORK_START = dt_time(9, 0)
    WORK_END = dt_time(23, 0)
    SLOT_STEP = 30
    
    all_times = []
    current_time = WORK_START
    while current_time < WORK_END:
        all_times.append(current_time.strftime('%H:%M'))
        current_time = (datetime.combine(date, current_time) + timedelta(minutes=SLOT_STEP)).time()
    
    blocked_slots = BlockedSlot.objects.filter(date=date)
    existing_bookings = Booking.objects.filter(
        appointment_datetime__date=date,
        status__in=['pending', 'confirmed']
    ).prefetch_related('services') # <-- ИЗМЕНЕНО
    
    current_tz = timezone.get_current_timezone()
    free_times = []
    
    for time_str in all_times:
        hour, minute = map(int, time_str.split(':'))
        slot_start_naive = datetime.combine(date, dt_time(hour, minute))
        slot_end_naive = slot_start_naive + timedelta(minutes=30)
        
        slot_start = timezone.make_aware(slot_start_naive, current_tz)
        slot_end = timezone.make_aware(slot_end_naive, current_tz)
        
        is_blocked = False
        for blocked in blocked_slots:
            if blocked.is_full_day:
                is_blocked = True
                break
            if blocked.start_time and blocked.end_time:
                blocked_start = timezone.make_aware(datetime.combine(date, blocked.start_time), current_tz)
                blocked_end = timezone.make_aware(datetime.combine(date, blocked.end_time), current_tz)
                if slot_start < blocked_end and slot_end > blocked_start:
                    is_blocked = True
                    break
        
        if is_blocked:
            continue
        
        is_booked = False
        for booking in existing_bookings:
            booking_duration = sum(s.duration for s in booking.services.all() if s.duration) # <-- ИЗМЕНЕНО
            booking_start = booking.appointment_datetime
            booking_end = booking_start + timedelta(minutes=booking_duration)
            
            if slot_start < booking_end and slot_end > booking_start:
                is_booked = True
                break
        
        if not is_booked:
            free_times.append(time_str)
    
    bookings_info = []
    for booking in existing_bookings:
        services_names = ", ".join([s.name for s in booking.services.all()]) # <-- ИЗМЕНЕНО
        bookings_info.append({
            'client_name': booking.client_name,
            'time': booking.appointment_datetime.strftime('%H:%M'),
            'services': services_names
        })
    
    return JsonResponse({
        'free_times': free_times,
        'total_slots': len(all_times),
        'free_slots': len(free_times),
        'has_bookings': existing_bookings.exists(),
        'bookings': bookings_info
    })


# =============================================
# API: ПРОВЕРКА EMAIL
# =============================================
@require_POST
def check_email_view(request):
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()

        if not email:
            return JsonResponse({'error': 'Email не указан'}, status=400)

        client = Client.objects.filter(email=email, is_verified=True).first()

        if client:
            return JsonResponse({
                'is_known': True,
                'message': f'С возвращением! У вас уже {client.total_bookings} записей.'
            })
        else:
            return JsonResponse({
                'is_known': False,
                'message': 'Новый клиент. Требуется подтверждение email.'
            })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат данных'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Ошибка сервера'}, status=500)


# =============================================
# API: ОТПРАВКА КОДА ПОДТВЕРЖДЕНИЯ
# =============================================
@require_POST
def send_email_code_view(request):
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()

        if not email:
            return JsonResponse({'error': 'Email не указан'}, status=400)

        recent_codes = EmailVerificationCode.objects.filter(
            email=email,
            created_at__gte=timezone.now() - timedelta(seconds=60)
        )
        if recent_codes.exists():
            return JsonResponse({'error': 'Подождите 1 минуту перед повторной отправкой'}, status=429)

        verification = EmailVerificationCode.generate_code(email)

        try:
            send_mail(
                subject='Код подтверждения записи — Sasha Sugar',
                message=f'Здравствуйте! Ваш код для подтверждения записи: {verification.code}\n\nКод действителен 10 минут.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            return JsonResponse({'success': True, 'message': 'Код отправлен на почту'})
        except Exception as e:
            verification.delete()
            return JsonResponse({'error': 'Не удалось отправить письмо. Проверьте адрес.'}, status=500)
    except Exception as e:
        return JsonResponse({'error': 'Ошибка сервера'}, status=500)


# =============================================
# API: ПРОВЕРКА КОДА
# =============================================
@require_POST
def verify_email_code_view(request):
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        code = data.get('code', '').strip()

        verification = EmailVerificationCode.objects.filter(
            email=email,
            is_used=False
        ).order_by('-created_at').first()

        if not verification:
            return JsonResponse({'error': 'Код не найден или уже использован'}, status=400)

        if verification.is_expired:
            return JsonResponse({'error': 'Срок действия кода истек. Запросите новый.'}, status=400)

        if verification.attempts >= 5:
            return JsonResponse({'error': 'Слишком много неверных попыток. Запросите новый код.'}, status=400)

        if verification.code != code:
            verification.attempts += 1
            verification.save()
            return JsonResponse({'error': f'Неверный код. Осталось попыток: {5 - verification.attempts}'}, status=400)

        verification.is_used = True
        verification.save()

        return JsonResponse({'success': True, 'message': 'Email успешно подтвержден'})
    except Exception as e:
        return JsonResponse({'error': 'Ошибка сервера'}, status=500)


# =============================================
# API: ПОЛУЧЕНИЕ СВОБОДНЫХ СЛОТОВ (ДЛЯ ФОРМЫ)
# =============================================
def get_available_times(request):
    """API endpoint для получения свободных слотов с учетом нескольких услуг"""
    date_str = request.GET.get('date')
    services_ids_str = request.GET.get('services_ids')

    if not date_str or not services_ids_str:
        return JsonResponse({'error': 'Не указана дата или услуги'}, status=400)

    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        services_ids = [int(id) for id in services_ids_str.split(',') if id]
        services = Service.objects.filter(id__in=services_ids, is_active=True)
        
        if not services.exists():
            return JsonResponse({'error': 'Услуги не найдены'}, status=404)
    except (ValueError, Service.DoesNotExist):
        return JsonResponse({'error': 'Неверные параметры'}, status=400)

    is_blocked = BlockedSlot.objects.filter(date=date, is_full_day=True).exists()

    if is_blocked:
        return JsonResponse({'is_blocked': True, 'times': [], 'blocked_count': 0})

    WORK_START = dt_time(9, 0)
    WORK_END = dt_time(23, 0)
    SLOT_STEP = 30

    duration_minutes = sum(s.duration for s in services if s.duration)
    buffer_minutes = 10
    total_duration = duration_minutes + buffer_minutes

    all_times = []
    current_time = WORK_START

    while current_time < WORK_END:
        slot_end_time = (datetime.combine(date, current_time) + timedelta(minutes=total_duration)).time()
        if slot_end_time <= WORK_END:
            all_times.append(current_time.strftime('%H:%M'))
        current_time = (datetime.combine(date, current_time) + timedelta(minutes=SLOT_STEP)).time()

    blocked_slots = BlockedSlot.objects.filter(date=date)
    existing_bookings = Booking.objects.filter(
        appointment_datetime__date=date,
        status__in=['pending', 'confirmed']
    ).prefetch_related('services')

    current_tz = timezone.get_current_timezone()
    available_times = []

    for time_str in all_times:
        hour, minute = map(int, time_str.split(':'))
        slot_start_naive = datetime.combine(date, dt_time(hour, minute))
        slot_end_naive = slot_start_naive + timedelta(minutes=duration_minutes)

        slot_start = timezone.make_aware(slot_start_naive, current_tz)
        slot_end = timezone.make_aware(slot_end_naive, current_tz)

        is_slot_blocked = False
        for blocked in blocked_slots:
            if blocked.is_full_day:
                is_slot_blocked = True
                break
            if blocked.start_time and blocked.end_time:
                blocked_start = timezone.make_aware(datetime.combine(date, blocked.start_time), current_tz)
                blocked_end = timezone.make_aware(datetime.combine(date, blocked.end_time), current_tz)
                if slot_start < blocked_end and slot_end > blocked_start:
                    is_slot_blocked = True
                    break

        if is_slot_blocked:
            continue

        is_slot_booked = False
        for booking in existing_bookings:
            booking_duration = sum(s.duration for s in booking.services.all() if s.duration)
            booking_start = booking.appointment_datetime
            booking_end = booking_start + timedelta(minutes=booking_duration)

            if slot_start < booking_end and slot_end > booking_start:
                is_slot_booked = True
                break

        if not is_slot_booked:
            available_times.append(time_str)

    return JsonResponse({
        'is_blocked': False,
        'times': available_times,
        'blocked_count': blocked_slots.count(),
        'total_duration': total_duration,
        'services_count': len(services)
    })


# =============================================
# СТРАНИЦА УСПЕШНОЙ ЗАПИСИ
# =============================================
def booking_success(request):
    return render(request, 'booking_app/booking_success.html')


def booking_create(request):
    """Создание записи клиентом"""
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            client_name = form.cleaned_data['client_name']
            phone = form.cleaned_data['phone']
            email = form.cleaned_data.get('email')
            date_str = form.cleaned_data['appointment_date']
            time_str = form.cleaned_data['appointment_time']
            
            services_ids_str = request.POST.get('services_ids', '')
            services_ids = [int(id) for id in services_ids_str.split(',') if id]
            
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
            
            booking = Booking.objects.create(
                client_name=client_name,
                phone=phone,
                email=email,
                appointment_datetime=aware_dt,
                status='confirmed'
            )
            
            if services_ids:
                services = Service.objects.filter(id__in=services_ids, is_active=True)
                booking.services.set(services)
            
            return redirect('booking_app:booking_success')
    else:
        form = BookingForm()
    
    return render(request, 'booking_app/booking_form.html', {'form': form})


# =============================================
# АДМИНКА: ЗАБЛОКИРОВАННЫЕ СЛОТЫ
# =============================================
class BlockedSlotListView(AdminRequiredMixin, ListView):
    model = BlockedSlot
    template_name = 'booking_app/admin/blocked_slots_list.html'
    context_object_name = 'blocked_slots'


class BlockedSlotAddView(AdminRequiredMixin, FormView):
    template_name = 'booking_app/admin/blocked_slot_form.html'
    form_class = BlockedSlotForm
    success_url = reverse_lazy('booking_app:blocked_slots_list')

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Временной слот успешно заблокирован')
        return super().form_valid(form)


class BlockedSlotDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk):
        slot = get_object_or_404(BlockedSlot, pk=pk)
        slot.delete()
        messages.success(request, 'Заблокированный слот удален')
        return redirect('booking_app:blocked_slots_list')


# =============================================
# АДМИНКА: ЗАПИСИ
# =============================================
class BookingsListView(AdminRequiredMixin, TemplateView):
    template_name = 'booking_app/admin/bookings_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        date_str = self.request.GET.get('date')
        if date_str:
            try:
                current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                current_date = timezone.now().date()
        else:
            current_date = timezone.now().date()

        bookings = Booking.objects.filter(
            appointment_datetime__date=current_date,
            status__in=['pending', 'confirmed']
        ).order_by('appointment_datetime')

        context['current_date'] = current_date
        context['bookings'] = bookings
        context['total_bookings'] = bookings.count()
        context['confirmed_count'] = bookings.filter(status='confirmed').count()
        context['pending_count'] = bookings.filter(status='pending').count()
        context['prev_date'] = current_date - timedelta(days=1)
        context['next_date'] = current_date + timedelta(days=1)
        context['today'] = timezone.now().date()
        
        return context


class AdminBookingCreateView(AdminRequiredMixin, FormView):
    template_name = 'booking_app/admin/booking_form.html'
    form_class = AdminBookingForm
    success_url = reverse_lazy('booking_app:bookings_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        service_id = self.request.GET.get('service')
        if service_id:
            try:
                service = Service.objects.get(id=service_id, is_active=True)
                form.initial['services'] = [service] # Для обратной совместимости
            except Service.DoesNotExist:
                pass
        return form

    def form_valid(self, form):
        date_str = self.request.POST.get('appointment_date')
        time_str = self.request.POST.get('appointment_time')

        if date_str and time_str:
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())

            # Получаем услуги
            services_ids_str = self.request.POST.get('services_ids', '')
            if services_ids_str:
                services_ids = [int(id) for id in services_ids_str.split(',') if id]
                services = Service.objects.filter(id__in=services_ids, is_active=True)
            else:
                services = form.cleaned_data.get('services', Service.objects.none())

            duration = sum(s.duration for s in services if s.duration)

            if is_time_slot_available(aware_dt, services=services, duration=duration):
                booking = form.save(commit=False)
                booking.appointment_datetime = aware_dt
                booking.status = form.cleaned_data.get('status', 'confirmed')
                booking.save()
                booking.services.set(services) # <-- Сохраняем M2M
                
                messages.success(self.request, f'Запись для {booking.client_name} создана')
                return redirect('booking_app:bookings_list')
            else:
                messages.error(self.request, 'Это время уже занято или заблокировано.')
                return self.form_invalid(form)

        return self.form_invalid(form)


class BookingConfirmView(AdminRequiredMixin, View):
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        booking.status = 'confirmed'
        booking.save()
        messages.success(request, f'Запись для {booking.client_name} подтверждена')
        return redirect('booking_app:bookings_list')


class BookingCancelView(AdminRequiredMixin, View):
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        booking.status = 'cancelled'
        booking.save()
        messages.success(request, f'Запись для {booking.client_name} отменена')
        return redirect('booking_app:bookings_list')
    

class BookingsScheduleView(AdminRequiredMixin, View):
    """Расписание записей в виде колонок по дням"""
    template_name = 'booking_app/admin/bookings_schedule.html'

    def get(self, request):
        period = request.GET.get('period', 'day')
        date_str = request.GET.get('date', timezone.now().date().isoformat())
        
        try:
            current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            current_date = timezone.now().date()

        if period == 'week':
            days_count = 7
            nav_step = 7
        else:
            days_count = 1
            nav_step = 1

        dates = []
        for i in range(days_count):
            dates.append(current_date + timedelta(days=i))

        schedule_data = []
        for date in dates:
            bookings = Booking.objects.filter(
                appointment_datetime__date=date,
                status__in=['pending', 'confirmed']
            ).prefetch_related('services').order_by('appointment_datetime') # <-- ИЗМЕНЕНО
            
            schedule_data.append({
                'date': date,
                'bookings': bookings
            })

        prev_date = current_date - timedelta(days=nav_step)
        next_date = current_date + timedelta(days=nav_step)

        context = {
            'period': period,
            'current_date': current_date,
            'schedule_data': schedule_data,
            'prev_date': prev_date.isoformat(),
            'next_date': next_date.isoformat(),
            'today': timezone.now().date(),
        }

        return render(request, self.template_name, context)