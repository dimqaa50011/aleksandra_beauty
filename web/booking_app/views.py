import json
import logging
from datetime import datetime, timedelta, time as dt_time
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import ListView, TemplateView, FormView, View

from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

import firebase_admin
from firebase_admin import credentials, messaging

from .models import Booking, BlockedSlot, DayOff, DeviceFCMToken, EmailVerificationCode, Client, PushSubscription
from .forms import BookingForm, AdminBookingForm, BlockedSlotForm
from beauty_app.models import Service, ServiceCategory

logger = logging.getLogger(__name__)

# ==========================================
# ИНИЦИАЛИЗАЦИЯ FIREBASE И ОТПРАВКА ПУШЕЙ
# ==========================================

if not firebase_admin._apps:
    cred_path = Path(__file__).parent.parent / 'firebase-credentials.json'
    if cred_path.exists():
        cred = credentials.Certificate(str(cred_path))
        firebase_admin.initialize_app(cred)
        print("✅ Firebase инициализирован")
    else:
        print(f"⚠️ Файл {cred_path} не найден. FCM работать не будет.")


def send_fcm_notification(title, body, url=None):
    """Отправляет push-уведомление всем зарегистрированным мобильным устройствам через FCM"""
    tokens = DeviceFCMToken.objects.filter(is_active=True).values_list('token', flat=True)
    
    if not tokens:
        print("ℹ️ Нет зарегистрированных FCM-токенов")
        return
    
    for token in tokens:
        try:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={'url': url} if url else {},
                token=token,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(color='#f2a6b0', sound='default'),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(aps=messaging.Aps(sound='default', badge=1)),
                ),
            )
            response = messaging.send(message)
            print(f"✅ FCM push отправлен: {response}")
            
        except messaging.UnregisteredError:
            DeviceFCMToken.objects.filter(token=token).update(is_active=False)
            print(f"🗑️ Токен недействителен: {token[:40]}...")
        except Exception as e:
            print(f"❌ Ошибка FCM для токена {token[:40]}...: {e}")


try:
    from pywebpush import webpush, WebPushException
    HAS_WEBPUSH = True
except ImportError:
    HAS_WEBPUSH = False


def send_push_notification(title, body, url=None):
    """Отправляет пуш всем админам через Web Push (для браузера/PWA)"""
    if not HAS_WEBPUSH:
        logger.warning("⚠️ pywebpush не установлен, отправка пушей пропущена")
        return
    
    subscriptions = PushSubscription.objects.all()
    if not subscriptions.exists():
        logger.info("ℹ️ Нет активных подписок на пуши в базе")
        return
    
    vapid_private_key = getattr(settings, 'VAPID_PRIVATE_KEY', '')
    vapid_admin_email = getattr(settings, 'VAPID_ADMIN_EMAIL', 'admin@example.com')
    
    if not vapid_private_key or vapid_private_key == 'None':
        logger.error("❌ VAPID_PRIVATE_KEY пустой или равен 'None'. Проверь .env.prod")
        return

    vapid_claims = {'sub': f'mailto:{vapid_admin_email}'}
    payload = json.dumps({'title': title, 'body': body, 'url': url or '/admin-dashboard/bookings/'})
    
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={'endpoint': sub.endpoint, 'keys': {'p256dh': sub.p256dh, 'auth': sub.auth}},
                data=payload,
                vapid_private_key=vapid_private_key,
                vapid_claims=vapid_claims,
            )
            logger.info(f"✅ WebPush успешно отправлен пользователю {sub.user.username}")
        except WebPushException as e:
            logger.error(f"❌ Ошибка WebPush для {sub.user.username}: {e}")
            if e.response and e.response.status_code in [404, 410]:
                sub.delete()
                logger.info(f"🗑️ Удалена невалидная подписка {sub.user.username}")
        except Exception as e:
            logger.error(f"❌ Критическая ошибка при отправке пуша {sub.user.username}: {e}", exc_info=True)


# ==========================================
# API ДЛЯ МОБИЛЬНОГО ПРИЛОЖЕНИЯ
# ==========================================
@csrf_exempt
@api_view(['POST'])
def app_login(request):
    """Вход по логину/паролю, возвращает токен"""
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')
    
    print(f"🔐 Попытка входа: username='{username}', password_len={len(password)}")
    
    user = authenticate(username=username, password=password)
    
    if user is None:
        print(f"❌ Аутентификация не удалась для '{username}'")
        return JsonResponse({'error': 'Неверные данные'}, status=401)
    
    print(f"✅ Аутентификация прошла, проверяем is_staff: {user.is_staff}")
    
    if not user.is_staff:
        print(f"❌ Пользователь '{username}' не является staff (is_staff={user.is_staff})")
        return JsonResponse({'error': 'Неверные данные'}, status=401)
    
    token, _ = Token.objects.get_or_create(user=user)
    print(f"✅ Успешный вход: {username}, токен: {token.key[:20]}...")
    return JsonResponse({'token': token.key, 'username': user.username})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def app_register_fcm_token(request):
    token = request.data.get('token', '').strip()
    platform = request.data.get('platform', '').strip()
    device_name = request.data.get('device_name', '').strip()
    
    if not token:
        return JsonResponse({'error': 'Token is required'}, status=400)
    
    obj, created = DeviceFCMToken.objects.update_or_create(
        token=token,
        defaults={'user': request.user, 'platform': platform, 'device_name': device_name, 'is_active': True}
    )
    action = 'создан' if created else 'обновлён'
    print(f"✅ FCM токен {action}: {request.user.username} ({platform})")
    return JsonResponse({'success': True, 'created': created})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def app_notifications(request):
    since_id = int(request.GET.get('since', 0))
    bookings = Booking.objects.filter(
        id__gt=since_id,
        created_at__gte=timezone.now() - timedelta(hours=48),
    ).order_by('id')[:20]
    
    result = []
    for b in bookings:
        services = ", ".join([s.name for s in b.services.all()])
        result.append({
            'id': b.id,
            'title': f'🔔 Новая запись: {b.client_name}',
            'body': f'{services}\n{b.appointment_datetime.strftime("%d.%m %H:%M")}\n{b.phone}',
            'url': f'/admin-dashboard/bookings/{b.pk}/edit/',
        })
    return JsonResponse(result, safe=False)


@csrf_exempt
@require_POST
def save_push_subscription(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Не авторизован'}, status=401)
    try:
        data = json.loads(request.body)
        subscription = data['subscription']
        PushSubscription.objects.update_or_create(
            user=request.user,
            endpoint=subscription['endpoint'],
            defaults={'p256dh': subscription['keys']['p256dh'], 'auth': subscription['keys']['auth']}
        )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ==========================================
# СОЗДАНИЕ ЗАПИСЕЙ (КЛИЕНТ И МИНИ-АПЫ)
# ==========================================

def booking_create(request):
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
                client_name=client_name, phone=phone, email=email,
                appointment_datetime=aware_dt, status='confirmed'
            )
            
            services_names = ""
            if services_ids:
                services = Service.objects.filter(id__in=services_ids, is_active=True)
                booking.services.set(services)
                services_names = ", ".join([s.name for s in services])
            
            # ОТПРАВКА УВЕДОМЛЕНИЙ
            send_push_notification('🔔 Новая запись!', f'{client_name} записался на {services_names}', '/admin-dashboard/bookings/')
            send_fcm_notification(f'🔔 Новая запись: {client_name}', f'{services_names}\n{aware_dt.strftime("%d.%m %H:%M")}', f'/admin-dashboard/bookings/{booking.pk}/edit/')
            
            return redirect('booking_app:booking_success')
    else:
        form = BookingForm()
    return render(request, 'booking_app/booking_form.html', {'form': form})


def vk_booking_view(request):
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
            
            services_ids_str = request.POST.get('services_ids', '')
            services_names = ""
            if services_ids_str:
                services_ids = [int(id) for id in services_ids_str.split(',') if id]
                services = Service.objects.filter(id__in=services_ids, is_active=True)
                booking.services.set(services)
                services_names = ", ".join([s.name for s in services])
            
            # ОТПРАВКА УВЕДОМЛЕНИЙ
            send_fcm_notification(f'🔔 Новая запись (VK): {booking.client_name}', f'{services_names}\n{aware_dt.strftime("%d.%m %H:%M")}', f'/admin-dashboard/bookings/{booking.pk}/edit/')

            if email:
                client, created = Client.objects.get_or_create(email=email)
                client.total_bookings += 1
                client.is_verified = True
                client.save()
                try:
                    send_mail('🌸 Ваша запись в Sasha Sugar подтверждена!',
                              f"Здравствуйте, {booking.client_name}!\n\nВаша запись на {date_str} в {time_str} ({services_names}) успешно оформлена.\n\nЖдем вас по адресу: Спасский переулок, 7",
                              settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
                except Exception:
                    pass
            return render(request, 'booking_app/vk_success.html', {'booking': booking})
    else:
        form = BookingForm()
    return render(request, 'booking_app/vk_booking.html', {'form': form})


def telegram_booking_view(request):
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
            
            services_ids_str = request.POST.get('services_ids', '')
            services_names = ""
            if services_ids_str:
                services_ids = [int(id) for id in services_ids_str.split(',') if id]
                services = Service.objects.filter(id__in=services_ids, is_active=True)
                booking.services.set(services)
                services_names = ", ".join([s.name for s in services])
            
            # ОТПРАВКА УВЕДОМЛЕНИЙ
            send_fcm_notification(f'🔔 Новая запись (Telegram): {booking.client_name}', f'{services_names}\n{aware_dt.strftime("%d.%m %H:%M")}', f'/admin-dashboard/bookings/{booking.pk}/edit/')

            if email:
                client, created = Client.objects.get_or_create(email=email)
                client.total_bookings += 1
                client.is_verified = True
                client.save()
                try:
                    send_mail('🌸 Ваша запись в Sasha Sugar подтверждена!',
                              f"Здравствуйте, {booking.client_name}!\n\nВаша запись на {date_str} в {time_str} ({services_names}) успешно оформлена.\n\nЖдем вас по адресу: Спасский переулок, 7",
                              settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
                except Exception:
                    pass
            return render(request, 'booking_app/telegram_success.html', {'booking': booking})
    else:
        form = BookingForm()
    return render(request, 'booking_app/telegram_booking.html', {'form': form})


def max_booking_view(request):
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
            
            services_ids_str = request.POST.get('services_ids', '')
            services_names = ""
            if services_ids_str:
                services_ids = [int(id) for id in services_ids_str.split(',') if id]
                services = Service.objects.filter(id__in=services_ids, is_active=True)
                booking.services.set(services)
                services_names = ", ".join([s.name for s in services])
            
            # ОТПРАВКА УВЕДОМЛЕНИЙ
            send_fcm_notification(f'🔔 Новая запись (MAX): {booking.client_name}', f'{services_names}\n{aware_dt.strftime("%d.%m %H:%M")}', f'/admin-dashboard/bookings/{booking.pk}/edit/')

            if email:
                client, created = Client.objects.get_or_create(email=email)
                client.total_bookings += 1
                client.is_verified = True
                client.save()
                try:
                    send_mail('🌸 Ваша запись в Sasha Sugar подтверждена!',
                              f"Здравствуйте, {booking.client_name}!\n\nВаша запись на {date_str} в {time_str} ({services_names}) успешно оформлена.\n\nЖдем вас по адресу: Спасский переулок, 7",
                              settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
                except Exception:
                    pass
            return render(request, 'booking_app/max_success.html', {'booking': booking})
    else:
        form = BookingForm()
    return render(request, 'booking_app/max_booking.html', {'form': form})


@csrf_exempt
@require_POST
def api_create_booking(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат JSON'}, status=400)

    client_name = data.get('client_name', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    date_str = data.get('date')
    time_str = data.get('time')
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
        appointment_datetime = timezone.make_aware(datetime.combine(date, time), timezone.get_current_timezone())
    except ValueError:
        return JsonResponse({'error': 'Неверный формат даты или времени'}, status=400)

    total_duration = sum(s.duration for s in services if s.duration)

    if not is_time_slot_available(appointment_datetime, services=services, duration=total_duration):
        return JsonResponse({'error': 'Это время уже занято или заблокировано'}, status=409)

    booking = Booking.objects.create(
        client_name=client_name, phone=phone, email=email if email else None,
        appointment_datetime=appointment_datetime, status='confirmed'
    )
    booking.services.set(services)

    services_names = ", ".join([s.name for s in services])
    
    # ОТПРАВКА УВЕДОМЛЕНИЙ
    send_fcm_notification(f'🔔 Новая запись (API): {client_name}', f'{services_names}\n{appointment_datetime.strftime("%d.%m %H:%M")}', f'/admin-dashboard/bookings/{booking.id}/edit/')

    if email:
        client, created = Client.objects.get_or_create(email=email)
        client.total_bookings += 1
        client.is_verified = True
        client.save()
        try:
            send_mail('🌸 Ваша запись в Sasha Sugar подтверждена!',
                      f"Здравствуйте, {client_name}!\n\nВаша запись успешно оформлена.\n\n📅 Дата: {date_str}\n⏰ Время: {time_str}\n💅 Услуги: {services_names}\n📍 Адрес: Санкт-Петербург, Спасский переулок, 7",
                      settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        except Exception as e:
            print(f"Ошибка отправки письма: {e}")

    return JsonResponse({
        'success': True, 'booking_id': booking.id, 'message': 'Запись успешно создана',
        'booking_details': {
            'client_name': booking.client_name, 'services': [s.name for s in services],
            'date': booking.appointment_datetime.strftime('%Y-%m-%d'),
            'time': booking.appointment_datetime.strftime('%H:%M'),
            'status': booking.get_status_display()
        }
    }, status=201)


# ==========================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ И АДМИНКА
# ==========================================

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = reverse_lazy('beauty_app:login')
    permission_denied_message = 'Доступ запрещён. Требуются права администратора.'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return render(self.request, 'beauty_app/auth/access_denied.html', status=403)
        return redirect(self.login_url)


def is_time_slot_available(new_start_time, services=None, duration=None):
    if duration is None and services:
        duration = sum(s.duration for s in services if s.duration)
    elif duration is None:
        duration = 60

    new_end_time = new_start_time + timedelta(minutes=duration)
    target_date = new_start_time.date()
    current_tz = timezone.get_current_timezone()

    blocked_slots = BlockedSlot.objects.filter(date=target_date)
    for slot in blocked_slots:
        if slot.is_full_day:
            return False
        if slot.start_time and slot.end_time:
            slot_start = timezone.make_aware(datetime.combine(target_date, slot.start_time), current_tz)
            slot_end = timezone.make_aware(datetime.combine(target_date, slot.end_time), current_tz)
            if new_start_time < slot_end and new_end_time > slot_start:
                return False    

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
    date_str = request.GET.get('date')
    if not date_str:
        return JsonResponse({'error': 'Не указана дата'}, status=400)
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Неверный формат даты'}, status=400)
    
    WORK_START, WORK_END, SLOT_STEP = dt_time(9, 0), dt_time(23, 0), 30
    all_times = []
    current_time = WORK_START
    while current_time < WORK_END:
        all_times.append(current_time.strftime('%H:%M'))
        current_time = (datetime.combine(date, current_time) + timedelta(minutes=SLOT_STEP)).time()
    
    blocked_slots = BlockedSlot.objects.filter(date=date)
    existing_bookings = Booking.objects.filter(
        appointment_datetime__date=date, status__in=['pending', 'confirmed']
    ).prefetch_related('services')
    
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
            booking_duration = sum(s.duration for s in booking.services.all() if s.duration)
            booking_start = booking.appointment_datetime
            booking_end = booking_start + timedelta(minutes=booking_duration)
            if slot_start < booking_end and slot_end > booking_start:
                is_booked = True
                break
        
        if not is_booked:
            free_times.append(time_str)
    
    bookings_info = [{
        'client_name': b.client_name,
        'time': b.appointment_datetime.strftime('%H:%M'),
        'services': ", ".join([s.name for s in b.services.all()])
    } for b in existing_bookings]
    
    return JsonResponse({
        'free_times': free_times, 'total_slots': len(all_times), 'free_slots': len(free_times),
        'has_bookings': existing_bookings.exists(), 'bookings': bookings_info
    })


@require_POST
def check_email_view(request):
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        if not email:
            return JsonResponse({'error': 'Email не указан'}, status=400)
        client = Client.objects.filter(email=email, is_verified=True).first()
        if client:
            return JsonResponse({'is_known': True, 'message': f'С возвращением! У вас уже {client.total_bookings} записей.'})
        return JsonResponse({'is_known': False, 'message': 'Новый клиент. Требуется подтверждение email.'})
    except Exception:
        return JsonResponse({'error': 'Ошибка сервера'}, status=500)


@require_POST
def send_email_code_view(request):
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        if not email:
            return JsonResponse({'error': 'Email не указан'}, status=400)
        if EmailVerificationCode.objects.filter(email=email, created_at__gte=timezone.now() - timedelta(seconds=60)).exists():
            return JsonResponse({'error': 'Подождите 1 минуту перед повторной отправкой'}, status=429)
        
        verification = EmailVerificationCode.generate_code(email)
        try:
            send_mail('Код подтверждения записи — Sasha Sugar',
                      f'Здравствуйте! Ваш код для подтверждения записи: {verification.code}\n\nКод действителен 10 минут.',
                      settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
            return JsonResponse({'success': True, 'message': 'Код отправлен на почту'})
        except Exception:
            verification.delete()
            return JsonResponse({'error': 'Не удалось отправить письмо. Проверьте адрес.'}, status=500)
    except Exception:
        return JsonResponse({'error': 'Ошибка сервера'}, status=500)


@require_POST
def verify_email_code_view(request):
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        code = data.get('code', '').strip()
        verification = EmailVerificationCode.objects.filter(email=email, is_used=False).order_by('-created_at').first()
        
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
    except Exception:
        return JsonResponse({'error': 'Ошибка сервера'}, status=500)


def get_available_times(request):
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

    if BlockedSlot.objects.filter(date=date, is_full_day=True).exists():
        return JsonResponse({'is_blocked': True, 'times': [], 'blocked_count': 0})

    WORK_START, WORK_END, SLOT_STEP = dt_time(9, 0), dt_time(23, 0), 30
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
        appointment_datetime__date=date, status__in=['pending', 'confirmed']
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
        'is_blocked': False, 'times': available_times, 'blocked_count': blocked_slots.count(),
        'total_duration': total_duration, 'services_count': len(services)
    })


def booking_success(request):
    return render(request, 'booking_app/booking_success.html')


def booking_edit(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    if request.method == 'POST':
        form = AdminBookingForm(request.POST, instance=booking)
        if form.is_valid():
            date_str = form.cleaned_data['appointment_date']
            time_str = form.cleaned_data['appointment_time']
            services_ids_str = request.POST.get('services_ids', '')
            
            if services_ids_str:
                services_ids = [int(id) for id in services_ids_str.split(',') if id]
                services = Service.objects.filter(id__in=services_ids, is_active=True)
            else:
                services = form.cleaned_data.get('services', booking.services.all())
            
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
            duration = sum(s.duration for s in services if s.duration)
            new_end_time = aware_dt + timedelta(minutes=duration)
            
            conflicting = Booking.objects.filter(
                appointment_datetime__date=aware_dt.date(), status__in=['pending', 'confirmed']
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
                return render(request, 'booking_app/admin/booking_edit.html', {'form': form, 'booking': booking})
            
            booking = form.save(commit=False)
            booking.appointment_datetime = aware_dt
            booking.save()
            booking.services.set(services)
            
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
    return render(request, 'booking_app/admin/booking_edit.html', {'form': form, 'booking': booking})


def get_services_by_category(request):
    category_id = request.GET.get('category_id')
    if not category_id:
        return JsonResponse({'services': []})
    try:
        services = Service.objects.filter(category_id=category_id, is_active=True).values('id', 'name', 'price', 'duration')
        return JsonResponse({'services': list(services)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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


class BookingsListView(AdminRequiredMixin, TemplateView):
    template_name = 'booking_app/admin/bookings_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        date_str = self.request.GET.get('date')
        try:
            current_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
        except ValueError:
            current_date = timezone.now().date()

        bookings = Booking.objects.filter(
            appointment_datetime__date=current_date, status__in=['pending', 'confirmed']
        ).order_by('appointment_datetime')

        context.update({
            'current_date': current_date, 'bookings': bookings, 'total_bookings': bookings.count(),
            'confirmed_count': bookings.filter(status='confirmed').count(),
            'pending_count': bookings.filter(status='pending').count(),
            'prev_date': current_date - timedelta(days=1),
            'next_date': current_date + timedelta(days=1),
            'today': timezone.now().date(),
        })
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
                form.initial['services'] = [service]
            except Service.DoesNotExist:
                pass
        return form

    def form_valid(self, form):
        date_str = self.request.POST.get('appointment_date')
        time_str = self.request.POST.get('appointment_time')

        if date_str and time_str:
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())

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
                booking.services.set(services)
                
                services_names = ", ".join([s.name for s in services])
                # ОТПРАВКА УВЕДОМЛЕНИЙ
                send_fcm_notification(f'🔔 Новая запись (Админ): {booking.client_name}', f'{services_names}\n{aware_dt.strftime("%d.%m %H:%M")}', f'/admin-dashboard/bookings/{booking.pk}/edit/')
                
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
    template_name = 'booking_app/admin/bookings_schedule.html'

    def get(self, request):
        period = request.GET.get('period', 'day')
        date_str = request.GET.get('date', timezone.now().date().isoformat())
        
        try:
            current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            current_date = timezone.now().date()

        days_count = 7 if period == 'week' else 1
        nav_step = 7 if period == 'week' else 1

        dates = [current_date + timedelta(days=i) for i in range(days_count)]
        schedule_data = []
        
        for date in dates:
            bookings = Booking.objects.filter(
                appointment_datetime__date=date, status__in=['pending', 'confirmed']
            ).prefetch_related('services').order_by('appointment_datetime')
            schedule_data.append({'date': date, 'bookings': bookings})

        context = {
            'period': period, 'current_date': current_date, 'schedule_data': schedule_data,
            'prev_date': (current_date - timedelta(days=nav_step)).isoformat(),
            'next_date': (current_date + timedelta(days=nav_step)).isoformat(),
            'today': timezone.now().date(),
        }
        return render(request, self.template_name, context)