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
from datetime import datetime, timedelta, time as dt_time
import json

from .models import Booking, BlockedSlot, DayOff, EmailVerificationCode, Client
from .forms import BookingForm, AdminBookingForm, BlockedSlotForm
from beauty_app.models import Service, ServiceCategory

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from django.shortcuts import render
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from .models import Booking, Client
from .forms import BookingForm
from django.core.mail import send_mail
from django.conf import settings


def get_services_by_category(request):
    """Возвращает список услуг конкретной категории в формате JSON"""
    category_id = request.GET.get('category_id')
    
    if not category_id:
        return JsonResponse({'services': []})
    
    try:
        # Фильтруем услуги по категории и статусу is_active
        services = Service.objects.filter(
            category_id=category_id, 
            is_active=True
        ).values('id', 'name', 'price')
        
        return JsonResponse({'services': list(services)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def vk_booking_view(request):
    """Страница записи для VK Mini App (без шапки и подвала сайта)"""
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            # Стандартная логика сохранения (такая же, как на сайте)
            date_str = form.cleaned_data['appointment_date']
            time_str = form.cleaned_data['appointment_time']
            service = form.cleaned_data['service']
            email = form.cleaned_data['email']
            
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
            
            booking = form.save(commit=False)
            booking.appointment_datetime = aware_dt
            booking.save()
            
            # Обновляем CRM
            if email:
                client, created = Client.objects.get_or_create(email=email)
                client.total_bookings += 1
                client.is_verified = True
                client.save()
                
                # Отправка письма
                try:
                    send_mail(
                        subject='🌸 Ваша запись в Sasha Sugar подтверждена!',
                        message=f"Здравствуйте, {booking.client_name}!\n\nВаша запись на {date_str} в {time_str} ({service.name}) успешно оформлена.\n\nЖдем вас по адресу: Спасский переулок, 7",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                except Exception:
                    pass

            # Для ВК возвращаем простую страницу успеха, чтобы не делать редирект внутри iframe
            return render(request, 'booking_app/vk_success.html', {'booking': booking})
    else:
        form = BookingForm()
    
    return render(request, 'booking_app/vk_booking.html', {'form': form})

@csrf_exempt
@require_POST
def api_create_booking(request):
    """
    Защищённый API endpoint для создания записи.
    Требует API токен в заголовке X-API-Token.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Неверный формат JSON'}, status=400)

    # Извлекаем данные
    client_name = data.get('client_name', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    service_id = data.get('service_id')
    date_str = data.get('date')
    time_str = data.get('time')

    # Валидация
    if not client_name or not phone or not service_id or not date_str or not time_str:
        return JsonResponse({
            'error': 'Не заполнены обязательные поля'
        }, status=400)

    # Проверяем услугу
    try:
        service = Service.objects.get(id=service_id, is_active=True)
    except Service.DoesNotExist:
        return JsonResponse({'error': 'Услуга не найдена'}, status=404)

    # Проверяем дату и время
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        time = datetime.strptime(time_str, '%H:%M').time()
        appointment_datetime = timezone.make_aware(
            datetime.combine(date, time),
            timezone.get_current_timezone()
        )
    except ValueError:
        return JsonResponse({'error': 'Неверный формат даты или времени'}, status=400)

    # Проверяем доступность слота
    if not is_time_slot_available(appointment_datetime, service):
        return JsonResponse({
            'error': 'Это время уже занято или заблокировано'
        }, status=409)

    # Создаём запись
    booking = Booking.objects.create(
        client_name=client_name,
        phone=phone,
        email=email if email else None,
        service=service,
        appointment_datetime=appointment_datetime,
        status='confirmed'
    )

    # Обновляем CRM
    if email:
        client, created = Client.objects.get_or_create(email=email)
        client.total_bookings += 1
        client.is_verified = True
        client.save()

    # Отправляем письмо
    if email:
        try:
            send_mail(
                subject='🌸 Ваша запись в Sasha Sugar подтверждена!',
                message=f"""Здравствуйте, {client_name}!

Ваша запись успешно оформлена.

📅 Дата: {date_str}
⏰ Время: {time_str}
💅 Услуга: {service.name}
📍 Адрес: Санкт-Петербург, Спасский переулок, 7

С любовью, команда Sasha Sugar""",
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
            'service': booking.service.name,
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
def is_time_slot_available(new_start_time, service, duration=None):
    """
    Проверяет, свободен ли слот (учитывает записи и заблокированные слоты).
    new_start_time: timezone-aware datetime
    """
    if duration is None:
        duration = getattr(service, 'duration', 60)

    new_end_time = new_start_time + timedelta(minutes=duration)

    # 1. Проверяем существующие записи
    target_date = new_start_time.date()
    blocked_slots = BlockedSlot.objects.filter(date=target_date)

    for slot in blocked_slots:
        # Если слот заблокирован на весь день
        if slot.is_full_day:
            return False
        
        # Если слот заблокирован по времени
        if slot.start_time and slot.end_time:
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
def get_free_slots_for_admin(request):
    """API для админки: возвращает свободные слоты и информацию о записях"""
    date_str = request.GET.get('date')
    
    if not date_str:
        return JsonResponse({'error': 'Не указана дата'}, status=400)
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Неверный формат даты'}, status=400)
    
    # Параметры рабочего времени
    WORK_START = dt_time(9, 0)
    WORK_END = dt_time(23, 0)
    SLOT_STEP = 30
    
    # Генерируем все возможные слоты
    all_times = []
    current_time = WORK_START
    
    while current_time < WORK_END:
        all_times.append(current_time.strftime('%H:%M'))
        current_time = (datetime.combine(date, current_time) + timedelta(minutes=SLOT_STEP)).time()
    
    # Получаем заблокированные слоты и существующие записи
    blocked_slots = BlockedSlot.objects.filter(date=date)
    existing_bookings = Booking.objects.filter(
        appointment_datetime__date=date,
        status__in=['pending', 'confirmed']
    )
    
    current_tz = timezone.get_current_timezone()
    free_times = []
    
    for time_str in all_times:
        hour, minute = map(int, time_str.split(':'))
        slot_start_naive = datetime.combine(date, dt_time(hour, minute))
        slot_end_naive = slot_start_naive + timedelta(minutes=30)
        
        slot_start = timezone.make_aware(slot_start_naive, current_tz)
        slot_end = timezone.make_aware(slot_end_naive, current_tz)
        
        # Проверяем пересечение с заблокированными слотами
        is_blocked = False
        for blocked in blocked_slots:
            if blocked.is_full_day:
                is_blocked = True
                break
            
            if blocked.start_time and blocked.end_time:
                blocked_start = timezone.make_aware(
                    datetime.combine(date, blocked.start_time), current_tz
                )
                blocked_end = timezone.make_aware(
                    datetime.combine(date, blocked.end_time), current_tz
                )
                
                if slot_start < blocked_end and slot_end > blocked_start:
                    is_blocked = True
                    break
        
        if is_blocked:
            continue
        
        # Проверяем пересечение с существующими записями
        is_booked = False
        for booking in existing_bookings:
            booking_start = booking.appointment_datetime
            booking_end = booking_start + timedelta(minutes=getattr(booking.service, 'duration', 60))
            
            if slot_start < booking_end and slot_end > booking_start:
                is_booked = True
                break
        
        if not is_booked:
            free_times.append(time_str)
    
    # Формируем список записей на этот день
    bookings_info = []
    for booking in existing_bookings:
        bookings_info.append({
            'client_name': booking.client_name,
            'time': booking.appointment_datetime.strftime('%H:%M'),
            'service': booking.service.name
        })
    
    return JsonResponse({
        'free_times': free_times,
        'total_slots': len(all_times),
        'free_slots': len(free_times),
        'has_bookings': existing_bookings.exists(),
        'bookings': bookings_info
    })

# =============================================
# API: ПРОВЕРКА EMAIL (НОВЫЙ ЭНДПОИНТ)
# =============================================
@require_POST
def check_email_view(request):
    """Проверяет, был ли клиент раньше (для умной верификации)"""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()

        if not email:
            return JsonResponse({'error': 'Email не указан'}, status=400)

        # Проверяем, есть ли клиент в базе и подтвержден ли он
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
    """Генерирует и отправляет код на email"""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()

        if not email:
            return JsonResponse({'error': 'Email не указан'}, status=400)

        # Защита от спама: не даем запрашивать код чаще раза в 60 секунд
        recent_codes = EmailVerificationCode.objects.filter(
            email=email,
            created_at__gte=timezone.now() - timedelta(seconds=60)
        )
        if recent_codes.exists():
            return JsonResponse({'error': 'Подождите 1 минуту перед повторной отправкой'}, status=429)

        # Генерируем и сохраняем код
        verification = EmailVerificationCode.generate_code(email)

        # Отправляем письмо
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
    """Проверяет введенный пользователем код"""
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

        # Код верный! Помечаем как использованный
        verification.is_used = True
        verification.save()

        return JsonResponse({'success': True, 'message': 'Email успешно подтвержден'})

    except Exception as e:
        return JsonResponse({'error': 'Ошибка сервера'}, status=500)


# =============================================
# API: ПОЛУЧЕНИЕ СВОБОДНЫХ СЛОТОВ
# =============================================
def get_available_times(request):
    """API endpoint для получения свободных слотов"""
    date_str = request.GET.get('date')
    service_id = request.GET.get('service_id')

    if not date_str or not service_id:
        return JsonResponse({'error': 'Не указана дата или услуга'}, status=400)

    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        service = Service.objects.get(id=service_id, is_active=True)
    except (ValueError, Service.DoesNotExist):
        return JsonResponse({'error': 'Неверные параметры'}, status=400)

    # Проверяем, не заблокирован ли день полностью
    is_blocked = BlockedSlot.objects.filter(
        date=date,
        slot_type='full_day'
    ).exists()

    if is_blocked:
        return JsonResponse({
            'is_blocked': True,
            'times': [],
            'blocked_count': 0
        })

    # Параметры рабочего времени
    WORK_START = dt_time(9, 0)
    WORK_END = dt_time(23, 0)
    SLOT_STEP = 30

    # Длительность услуги + буфер на подготовку (10 минут)
    duration_minutes = getattr(service, 'duration', 60)
    buffer_minutes = 10
    total_duration = duration_minutes + buffer_minutes

    # Генерируем все возможные слоты
    all_times = []
    current_time = WORK_START

    while current_time < WORK_END:
        slot_end_time = (datetime.combine(date, current_time) + timedelta(minutes=total_duration)).time()

        if slot_end_time <= WORK_END:
            all_times.append(current_time.strftime('%H:%M'))

        current_time = (datetime.combine(date, current_time) + timedelta(minutes=SLOT_STEP)).time()

    # Получаем заблокированные слоты и существующие записи
    blocked_slots = BlockedSlot.objects.filter(date=date)
    existing_bookings = Booking.objects.filter(
        appointment_datetime__date=date,
        status__in=['pending', 'confirmed']
    )

    current_tz = timezone.get_current_timezone()
    available_times = []

    for time_str in all_times:
        hour, minute = map(int, time_str.split(':'))
        slot_start_naive = datetime.combine(date, dt_time(hour, minute))
        slot_end_naive = slot_start_naive + timedelta(minutes=duration_minutes)

        slot_start = timezone.make_aware(slot_start_naive, current_tz)
        slot_end = timezone.make_aware(slot_end_naive, current_tz)

        # Проверяем пересечение с заблокированными слотами
        is_slot_blocked = False
        for blocked in blocked_slots:
            blocked_start_naive = datetime.combine(date, blocked.start_time)
            blocked_end_naive = datetime.combine(date, blocked.end_time)

            blocked_start = timezone.make_aware(blocked_start_naive, current_tz)
            blocked_end = timezone.make_aware(blocked_end_naive, current_tz)

            if slot_start < blocked_end and slot_end > blocked_start:
                is_slot_blocked = True
                break

        if is_slot_blocked:
            continue

        # Проверяем пересечение с существующими записями
        is_slot_booked = False
        for booking in existing_bookings:
            booking_start = booking.appointment_datetime
            booking_end = booking_start + timedelta(minutes=duration_minutes)

            if slot_start < booking_end and slot_end > booking_start:
                is_slot_booked = True
                break

        if not is_slot_booked:
            available_times.append(time_str)

    return JsonResponse({
        'is_blocked': False,
        'times': available_times,
        'blocked_count': blocked_slots.count()
    })


# =============================================
# СТРАНИЦА УСПЕШНОЙ ЗАПИСИ
# =============================================
def booking_success(request):
    """Страница подтверждения успешной записи"""
    return render(request, 'booking_app/booking_success.html')


# =============================================
# СОЗДАНИЕ ЗАПИСИ КЛИЕНТОМ
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

        if form.is_valid():
            date_str = form.cleaned_data['appointment_date']
            time_str = form.cleaned_data['appointment_time']
            service = form.cleaned_data['service']
            email = form.cleaned_data['email']

            # Собираем datetime
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())

            # Сохраняем запись
            booking = form.save(commit=False)
            booking.appointment_datetime = aware_dt
            booking.save()

            # Обновляем или создаем клиента в CRM
            client, created = Client.objects.get_or_create(email=email)
            client.total_bookings += 1
            client.is_verified = True
            client.save()

            # Отправляем письмо с подтверждением
            try:
                send_mail(
                    subject='🌸 Ваша запись в Sasha Sugar подтверждена!',
                    message=f"""Здравствуйте, {booking.client_name}!

Спасибо, что выбрали студию Sasha Sugar. Ваша онлайн-запись успешно оформлена.

📅 Дата: {booking.appointment_datetime.strftime('%d.%m.%Y')}
⏰ Время: {booking.appointment_datetime.strftime('%H:%M')}
💅 Услуга: {booking.service.name}
📍 Адрес: Санкт-Петербург, Спасский переулок, 7

Если у вас изменились планы, пожалуйста, предупредите нас не менее чем за 24 часа.

С любовью и заботой о вашей красоте,
Команда Sasha Sugar""",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Ошибка отправки письма: {e}")

            return redirect('booking_app:booking_success')
    else:
        form = BookingForm(initial=initial_data)

    return render(request, 'booking_app/booking_form.html', {'form': form})


# =============================================
# АДМИНКА: ЗАБЛОКИРОВАННЫЕ СЛОТЫ
# =============================================
class BlockedSlotListView(AdminRequiredMixin, ListView):
    """Список заблокированных слотов"""
    model = BlockedSlot
    template_name = 'booking_app/admin/blocked_slots_list.html'
    context_object_name = 'blocked_slots'

class BlockedSlotAddView(AdminRequiredMixin, FormView): # Или CreateView, но FormView тоже ок с form.save()
    """Добавление заблокированного слота"""
    template_name = 'booking_app/admin/blocked_slot_form.html'
    form_class = BlockedSlotForm
    success_url = reverse_lazy('booking_app:blocked_slots_list')

    def form_valid(self, form):
        # form.save() автоматически создаст объект, так как это ModelForm
        form.save()
        messages.success(self.request, 'Временной слот успешно заблокирован')
        return super().form_valid(form)


class BlockedSlotDeleteView(AdminRequiredMixin, View):
    """Удаление заблокированного слота"""

    def post(self, request, pk):
        slot = get_object_or_404(BlockedSlot, pk=pk)
        slot.delete()
        messages.success(request, 'Заблокированный слот удален')
        return redirect('booking_app:blocked_slots_list')


# =============================================
# АДМИНКА: ЗАПИСИ
# =============================================
class BookingsListView(AdminRequiredMixin, ListView):
    """Страница списка всех записей клиентов"""
    model = Booking
    template_name = 'booking_app/admin/bookings_list.html'
    context_object_name = 'bookings'

    def get_queryset(self):
        return Booking.objects.all().order_by('appointment_datetime')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['today'] = timezone.now().date()
        return context


class AdminBookingCreateView(AdminRequiredMixin, FormView):
    """Ручное создание записи администратором"""
    template_name = 'booking_app/admin/booking_form.html'
    form_class = AdminBookingForm
    success_url = reverse_lazy('booking_app:bookings_list')

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
                return redirect('booking_app:bookings_list')
            else:
                messages.error(self.request, 'Это время уже занято или заблокировано.')
                return self.form_invalid(form)

        return self.form_invalid(form)


class BookingConfirmView(AdminRequiredMixin, View):
    """Подтверждение записи"""

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        booking.status = 'confirmed'
        booking.save()
        messages.success(request, f'Запись для {booking.client_name} подтверждена')
        return redirect('booking_app:bookings_list')


class BookingCancelView(AdminRequiredMixin, View):
    """Отмена/удаление записи"""

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        booking.status = 'cancelled'
        booking.save()
        messages.success(request, f'Запись для {booking.client_name} отменена')
        return redirect('booking_app:bookings_list')