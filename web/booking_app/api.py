from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta, time as dt_time
from rest_framework.decorators import api_view, permission_classes

# Импорты для очереди и задач
from django_q.tasks import async_task
from .tasks import schedule_reminders

from .models import Booking, BlockedSlot, Client
from .serializers import BookingSerializer, BlockDaySerializer
from beauty_app.models import Service, ServiceCategory


class AdminBookingUpdateAPIView(APIView):
    """
    PUT: Обновить запись (время, услуги) из мобильного приложения
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        
        date_str = request.data.get('date')
        time_str = request.data.get('time')
        services_ids = request.data.get('services_ids') # список ID или строка "1,2"

        if not date_str or not time_str or not services_ids:
            return Response({'error': 'Не все данные переданы'}, status=400)

        try:
            # Обновляем время
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())
            
            # Обновляем услуги
            if isinstance(services_ids, str):
                services_ids = [int(i) for i in services_ids.split(',') if i]
                
            services = Service.objects.filter(id__in=services_ids, is_active=True)
            
            # Сохраняем
            booking.appointment_datetime = aware_dt
            booking.save()
            booking.services.set(services)
            
            # === СБРАСЫВАЕМ ФЛАГИ И ОТПРАВЛЯЕМ SMS ===
            booking.reminded_24h = False
            booking.reminded_2h = False
            booking.reminded_15m = False
            booking.save()
            
            async_task('booking_app.tasks.send_event_sms_task', booking.id, 'edit')
            schedule_reminders(booking.id, booking.appointment_datetime)
            
            return Response({'success': True, 'message': 'Запись обновлена'})
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_admin_available_times(request):
    """Возвращает свободные слоты для админской формы записи"""
    date_str = request.GET.get('date')
    services_ids_str = request.GET.get('services_ids')
    
    if not date_str:
        return Response({'error': 'Не указана дата'}, status=400)
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Неверный формат даты'}, status=400)

    # Если услуги не выбраны, берем стандартную длительность (например, 60 минут)
    duration_minutes = 60
    if services_ids_str:
        try:
            services_ids = [int(id) for id in services_ids_str.split(',') if id]
            services = Service.objects.filter(id__in=services_ids, is_active=True)
            if services.exists():
                duration_minutes = sum(s.duration for s in services if s.duration)
        except ValueError:
            pass
    
    # Добавляем буфер 10 минут, как на клиенте
    total_duration = duration_minutes + 10

    WORK_START, WORK_END, SLOT_STEP = dt_time(9, 0), dt_time(22, 0), 30
    current_tz = timezone.get_current_timezone()
    
    # Проверяем, не заблокирован ли день полностью
    if BlockedSlot.objects.filter(date=date, is_full_day=True).exists():
        return Response({'times': [], 'is_blocked': True})

    blocked_slots = BlockedSlot.objects.filter(date=date)
    existing_bookings = Booking.objects.filter(
        appointment_datetime__date=date, status__in=['pending', 'confirmed']
    ).prefetch_related('services')

    available_times = []
    current_time = WORK_START

    while current_time < WORK_END:
        slot_start = timezone.make_aware(datetime.combine(date, current_time), current_tz)
        slot_end = slot_start + timedelta(minutes=total_duration)
        
        # Если запись выходит за конец рабочего дня — пропускаем
        if slot_end.time() > WORK_END:
            break

        is_free = True

        # Проверка блокировок по времени
        for blocked in blocked_slots:
            if blocked.start_time and blocked.end_time:
                b_start = timezone.make_aware(datetime.combine(date, blocked.start_time), current_tz)
                b_end = timezone.make_aware(datetime.combine(date, blocked.end_time), current_tz)
                if slot_start < b_end and slot_end > b_start:
                    is_free = False
                    break
        
        # Проверка существующих записей
        if is_free:
            for booking in existing_bookings:
                b_duration = sum(s.duration for s in booking.services.all() if s.duration)
                b_start = booking.appointment_datetime
                b_end = b_start + timedelta(minutes=b_duration)
                if slot_start < b_end and slot_end > b_start:
                    is_free = False
                    break

        if is_free:
            available_times.append(current_time.strftime('%H:%M'))

        current_time = (datetime.combine(date, current_time) + timedelta(minutes=SLOT_STEP)).time()

    return Response({'times': available_times, 'is_blocked': False})


class AdminClientsAPIView(APIView):
    """
    GET: Список клиентов (CRM) с поиском
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        search_query = request.query_params.get('search', '').strip()
        
        clients = Client.objects.all().order_by('-last_visit')
        if search_query:
            clients = clients.filter(email__icontains=search_query)

        # Ограничиваем до 100 последних для мобильного приложения
        clients = clients[:100]

        data = []
        for c in clients:
            data.append({
                'id': c.id,
                'email': c.email,
                'total_bookings': c.total_bookings,
                'last_visit': c.last_visit.strftime('%d.%m.%Y'),
                'is_verified': c.is_verified,
            })

        return Response({'clients': data}, status=status.HTTP_200_OK)


class AdminCalendarAPIView(APIView):
    """
    GET: Отдает сетку времени на день (или неделю) с статусами:
    free (свободно), booked (занято), blocked (выходной)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_str = request.query_params.get('date')
        period = request.query_params.get('period', 'day') # 'day' или 'week'
        
        if not date_str:
            return Response({'error': 'Не указана дата'}, status=400)

        try:
            start_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Неверный формат даты'}, status=400)

        days_count = 7 if period == 'week' else 1
        dates = [start_date + timedelta(days=i) for i in range(days_count)]
        
        # Рабочие часы
        WORK_START = dt_time(9, 0)
        WORK_END = dt_time(23, 30)
        SLOT_STEP = 30 # Шаг 30 минут
        
        result = {}

        for current_date in dates:
            date_key = current_date.strftime('%Y-%m-%d')
            result[date_key] = []
            
            # Получаем блокировки на этот день
            blocked_slots = BlockedSlot.objects.filter(date=current_date)
            is_full_day_blocked = blocked_slots.filter(is_full_day=True).exists()
            
            # Получаем записи
            bookings = Booking.objects.filter(
                appointment_datetime__date=current_date,
                status__in=['pending', 'confirmed']
            ).prefetch_related('services')

            # Генерируем слоты
            current_time = datetime.combine(current_date, WORK_START)
            end_time = datetime.combine(current_date, WORK_END)
            
            # Делаем время aware (с учетом часового пояса), чтобы сравнивать с базой
            current_tz = timezone.get_current_timezone()
            current_time = timezone.make_aware(current_time, current_tz)
            end_time = timezone.make_aware(end_time, current_tz)

            while current_time < end_time:
                time_str = current_time.strftime('%H:%M')
                slot_status = 'free'
                booking_data = None

                # 1. Проверяем, не заблокирован ли весь день
                if is_full_day_blocked:
                    slot_status = 'blocked'
                else:
                    # 2. Проверяем частичные блокировки (по времени)
                    for b in blocked_slots:
                        if b.start_time and b.end_time:
                            b_start = timezone.make_aware(datetime.combine(current_date, b.start_time), current_tz)
                            b_end = timezone.make_aware(datetime.combine(current_date, b.end_time), current_tz)
                            if b_start <= current_time < b_end:
                                slot_status = 'blocked'
                                break

                    # 3. Проверяем, есть ли запись в это время
                    if slot_status == 'free':
                        for booking in bookings:
                            booking_start = booking.appointment_datetime
                            
                            # Защита от нулевой длительности
                            duration = sum(s.duration for s in booking.services.all() if s.duration)
                            if not duration or duration <= 0:
                                duration = 30
                                
                            booking_end = booking_start + timedelta(minutes=duration)
                            
                            # Если текущий слот попадает в интервал записи
                            if booking_start <= current_time < booking_end:
                                slot_status = 'booked'
                                booking_data = {
                                    'id': booking.id,
                                    'client_name': booking.client_name,
                                    'phone': booking.phone,
                                    'status': booking.status,
                                    'services': [{'id': s.id, 'name': s.name} for s in booking.services.all()],
                                    'time': booking_start.strftime('%H:%M')
                                }
                                break

                result[date_key].append({
                    'time': time_str,
                    'status': slot_status,
                    'booking': booking_data
                })
                
                current_time += timedelta(minutes=SLOT_STEP)

        return Response({'calendar': result}, status=200)


class AdminBlockedSlotsAPIView(APIView):
    """
    GET: Список блокировок
    POST: Создать блокировку (на весь день или на конкретные часы)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        slots = BlockedSlot.objects.filter(date__gte=today).order_by('date', 'start_time')
        
        data = []
        for s in slots:
            data.append({
                'id': s.id,
                'date': s.date.strftime('%Y-%m-%d'),
                'is_full_day': s.is_full_day,
                'start_time': s.start_time.strftime('%H:%M') if s.start_time else None,
                'end_time': s.end_time.strftime('%H:%M') if s.end_time else None,
                'reason': s.reason,
                'slot_type_display': s.get_slot_type_display()
            })
        return Response({'slots': data}, status=status.HTTP_200_OK)

    def post(self, request):
        date_str = request.data.get('date')
        is_full_day = request.data.get('is_full_day', True)
        start_time_str = request.data.get('start_time')
        end_time_str = request.data.get('end_time')
        reason = request.data.get('reason', 'Личные дела')
        
        if not date_str:
            return Response({'error': 'Не указана дата'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Неверный формат даты'}, status=status.HTTP_400_BAD_REQUEST)

        start_time = None
        end_time = None
        current_tz = timezone.get_current_timezone()

        if not is_full_day:
            if not start_time_str or not end_time_str:
                return Response({'error': 'Укажите время начала и конца'}, status=400)
                
            try:
                start_time = datetime.strptime(start_time_str, '%H:%M').time()
                end_time = datetime.strptime(end_time_str, '%H:%M').time()
                if start_time >= end_time:
                    return Response({'error': 'Время начала должно быть раньше конца'}, status=400)
            except ValueError:
                return Response({'error': 'Неверный формат времени'}, status=400)

            # ПРОВЕРКА КОНФЛИКТОВ С ЗАПИСЯМИ
            block_start_dt = timezone.make_aware(datetime.combine(target_date, start_time), current_tz)
            block_end_dt = timezone.make_aware(datetime.combine(target_date, end_time), current_tz)

            bookings = Booking.objects.filter(
                appointment_datetime__date=target_date,
                status__in=['pending', 'confirmed']
            ).prefetch_related('services')

            for b in bookings:
                b_duration = sum(s.duration for s in b.services.all() if s.duration)
                b_start = b.appointment_datetime
                b_end = b_start + timedelta(minutes=b_duration)

                # Если запись пересекается с блокировкой
                if b_start < block_end_dt and b_end > block_start_dt:
                    return Response({
                        'error': f'Нельзя заблокировать это время. У вас запись на {b_start.strftime("%H:%M")} ({b.client_name})'
                    }, status=status.HTTP_409_CONFLICT)

        # Создаем блокировку
        slot = BlockedSlot.objects.create(
            date=target_date,
            is_full_day=is_full_day,
            start_time=start_time,
            end_time=end_time,
            reason=reason,
            slot_type='day_off' if is_full_day else 'personal'
        )
        
        return Response({'success': True, 'id': slot.id}, status=status.HTTP_201_CREATED)


class AdminBlockedSlotDeleteAPIView(APIView):
    """
    DELETE: Удалить блокировку (разблокировать день)
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        slot = get_object_or_404(BlockedSlot, pk=pk)
        slot.delete()
        return Response({'success': True}, status=status.HTTP_200_OK)


class ServiceListAPIView(APIView):
    """
    GET: Возвращает список всех активных услуг для выбора в мобильном приложении
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        services = Service.objects.filter(is_active=True).order_by('category', 'name')
        
        data = []
        for s in services:
            data.append({
                'id': s.id,
                'name': s.name,
                'price': int(s.price),
                'category_name': s.category.name if s.category else 'Без категории',
                'category_id': s.category.id if s.category else 0
            })
            
        return Response({'services': data}, status=status.HTTP_200_OK)


class AdminCategoriesAPIView(APIView):
    """
    GET: Список всех категорий
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        categories = ServiceCategory.objects.filter(is_active=True).order_by('order')
        data = [{'id': c.id, 'name': c.display_name} for c in categories]
        return Response({'categories': data})


class AdminBookingsListAPIView(APIView):
    """
    GET: Получить список записей на выбранную дату (по умолчанию — на сегодня)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_str = request.query_params.get('date', timezone.now().date().isoformat())
        
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Неверный формат даты. Ожидается YYYY-MM-DD'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        bookings = Booking.objects.filter(
            appointment_datetime__date=target_date,
            status__in=['pending', 'confirmed']
        ).prefetch_related('services').order_by('appointment_datetime')

        serializer = BookingSerializer(bookings, many=True)
        
        return Response({
            'bookings': serializer.data,
            'count': bookings.count()
        }, status=status.HTTP_200_OK)


class AdminBookingStatusAPIView(APIView):
    """
    POST: Подтвердить или отменить запись из мобильного приложения
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        new_status = request.data.get('status')
        
        if new_status not in ['confirmed', 'cancelled']:
            return Response(
                {'error': 'Неверный статус. Допустимо: confirmed, cancelled'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        booking.status = new_status
        booking.save()
        
        # === ОТПРАВЛЯЕМ SMS ПРИ ОТМЕНЕ ===
        if new_status == 'cancelled':
            async_task('booking_app.tasks.send_event_sms_task', booking.id, 'cancel')
        
        return Response({
            'success': True, 
            'status': booking.status,
            'message': f'Статус записи изменен на {booking.get_status_display()}'
        }, status=status.HTTP_200_OK)


class AdminBlockDayAPIView(APIView):
    """
    POST: Заблокировать целый день (выходной)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BlockDaySerializer(data=request.data)
        
        if serializer.is_valid():
            target_date = serializer.validated_data['date']
            reason = serializer.validated_data.get('reason', 'Выходной')
            
            # Создаем или обновляем блокировку на весь день
            slot, created = BlockedSlot.objects.get_or_create(
                date=target_date,
                is_full_day=True,
                defaults={'reason': reason, 'slot_type': 'day_off'}
            )
            
            return Response({
                'success': True, 
                'created': created,
                'message': 'День успешно заблокирован' if created else 'Этот день уже был заблокирован'
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)