from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta, time as dt_time
from rest_framework.decorators import api_view, permission_classes
from django.conf import settings

# Импорты для очереди и задач
from django_q.tasks import async_task

from booking_app.services.bonuses import set_bonuses, spend_bonuses_booking
from booking_app.services.slots import (
    calculate_services_duration,
    get_available_slots,
)
from .tasks import schedule_reminders

from .models import Booking, BlockedSlot, Client
from .serializers import BookingSerializer, BlockDaySerializer
from beauty_app.models import Service, ServiceCategory, Review

import logging

logger = logging.getLogger(__name__)


class AdminReviewsAPIView(APIView):
    """GET: Список всех отзывов"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reviews = Review.objects.all().order_by('-created_at')

        data = []
        for r in reviews:
            data.append({
                'id': r.id,
                'author_name': r.author_name,
                'text': r.text,
                'rating': r.rating,
                'service_name': r.service_name,
                'created_at': r.created_at.strftime('%d.%m.%Y %H:%M'),
                'is_active': r.is_active,
            })

        return Response({'reviews': data}, status=status.HTTP_200_OK)


class AdminReviewActionAPIView(APIView):
    """PATCH: Опубликовать/скрыть, DELETE: Удалить отзыв"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        is_active = request.data.get('is_active')

        if is_active is not None:
            review.is_active = is_active
            review.save()
            action = "опубликован" if is_active else "скрыт"
            return Response({'success': True, 'message': f'Отзыв {action}'}, status=status.HTTP_200_OK)

        return Response({'error': 'Нет данных для обновления'}, status=400)

    def delete(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        review.delete()
        return Response({'success': True, 'message': 'Отзыв удален'}, status=status.HTTP_200_OK)


class AdminBookingUpdateAPIView(APIView):
    """
    PUT: Обновить запись (время, услуги) из мобильного приложения.

    ВНИМАНИЕ: сейчас нет проверки на пересечение с другими записями.
    Админ может перенести запись на уже занятое время, что создаст накладку.
    Если нужно — добавить is_slot_free(..., apply_lead_time=False, exclude_booking_id=pk).
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)

        date_str = request.data.get('date')
        time_str = request.data.get('time')
        services_ids = request.data.get('services_ids')

        if not date_str or not time_str or not services_ids:
            return Response({'error': 'Не все данные переданы'}, status=400)

        try:
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            aware_dt = timezone.make_aware(naive_dt, timezone.get_current_timezone())

            if isinstance(services_ids, str):
                services_ids = [int(i) for i in services_ids.split(',') if i]

            services = Service.objects.filter(id__in=services_ids, is_active=True)

            booking.appointment_datetime = aware_dt
            booking.save()
            booking.services.set(services)

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
    """Свободные слоты для админской формы — БЕЗ лид-тайма (walk-in)."""
    date_str = request.GET.get('date')
    services_ids_str = request.GET.get('services_ids')

    if not date_str:
        return Response({'error': 'Не указана дата'}, status=400)

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Неверный формат даты'}, status=400)

    duration_minutes = 60
    if services_ids_str:
        try:
            services_ids = [int(id) for id in services_ids_str.split(',') if id]
            services = Service.objects.filter(id__in=services_ids, is_active=True)
            if services.exists():
                duration_minutes = calculate_services_duration(services)
        except ValueError:
            pass

    result = get_available_slots(target_date, duration_minutes, apply_lead_time=False)
    return Response({'times': result['times'], 'is_blocked': result['is_blocked']})


class AdminClientsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        search_query = request.query_params.get('search', '').strip()

        clients = Client.objects.all().order_by('-last_visit')
        if search_query:
            clients = clients.filter(name__icontains=search_query) | clients.filter(phone__icontains=search_query)

        clients = clients[:100]

        data = []
        for c in clients:
            data.append({
                'id': c.id,
                'name': c.name,
                'phone': c.phone,
                'total_bookings': c.total_bookings,
                'total_spent': int(c.total_spent),
                'last_visit': c.last_visit.strftime('%d.%m.%Y'),
            })

        return Response({'clients': data}, status=status.HTTP_200_OK)


class AdminCalendarAPIView(APIView):
    """
    GET: Сетка времени на день/неделю со статусами: free / booked / blocked.
    WORK_END=22:00 для консистентности с рабочими часами студии.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_str = request.query_params.get('date')
        period = request.query_params.get('period', 'day')

        if not date_str:
            return Response({'error': 'Не указана дата'}, status=400)

        try:
            start_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Неверный формат даты'}, status=400)

        days_count = 7 if period == 'week' else 1
        dates = [start_date + timedelta(days=i) for i in range(days_count)]

        WORK_START = dt_time(9, 0)
        WORK_END = dt_time(22, 0)
        SLOT_STEP = 30

        result = {}

        for current_date in dates:
            date_key = current_date.strftime('%Y-%m-%d')
            result[date_key] = []

            blocked_slots = BlockedSlot.objects.filter(date=current_date)
            is_full_day_blocked = blocked_slots.filter(is_full_day=True).exists()

            bookings = Booking.objects.filter(
                appointment_datetime__date=current_date,
                status__in=['pending', 'confirmed']
            ).prefetch_related('services')

            current_time = datetime.combine(current_date, WORK_START)
            end_time = datetime.combine(current_date, WORK_END)

            current_tz = timezone.get_current_timezone()
            current_time = timezone.make_aware(current_time, current_tz)
            end_time = timezone.make_aware(end_time, current_tz)

            while current_time < end_time:
                time_str = current_time.strftime('%H:%M')
                slot_status = 'free'
                booking_data = None

                if is_full_day_blocked:
                    slot_status = 'blocked'
                else:
                    for b in blocked_slots:
                        if b.start_time and b.end_time:
                            b_start = timezone.make_aware(datetime.combine(current_date, b.start_time), current_tz)
                            b_end = timezone.make_aware(datetime.combine(current_date, b.end_time), current_tz)
                            if b_start <= current_time < b_end:
                                slot_status = 'blocked'
                                break

                    if slot_status == 'free':
                        for booking in bookings:
                            booking_start = booking.appointment_datetime
                            duration = sum(s.duration for s in booking.services.all() if s.duration)
                            if not duration or duration <= 0:
                                duration = 30

                            booking_end = booking_start + timedelta(minutes=duration)

                            if booking_start <= current_time < booking_end:
                                slot_status = 'booked'
                                booking_data = {
                                    'id': booking.id,
                                    'client_id': booking.client.id if booking.client else 0,
                                    'client_name': booking.client_name,
                                    'phone': booking.phone,
                                    'status': booking.status,
                                    'services': [{'id': s.id, 'name': s.name} for s in booking.services.all()],
                                    'time': booking_start.strftime('%H:%M'),
                                    'is_start': current_time == booking_start
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

                if b_start < block_end_dt and b_end > block_start_dt:
                    return Response({
                        'error': f'Нельзя заблокировать это время. У вас запись на {b_start.strftime("%H:%M")} ({b.client_name})'
                    }, status=status.HTTP_409_CONFLICT)

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
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        slot = get_object_or_404(BlockedSlot, pk=pk)
        slot.delete()
        return Response({'success': True}, status=status.HTTP_200_OK)


class ServiceListAPIView(APIView):
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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        categories = ServiceCategory.objects.filter(is_active=True).order_by('order')
        data = [{'id': c.id, 'name': c.display_name} for c in categories]
        return Response({'categories': data})


class AdminBookingsListAPIView(APIView):
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


class AdminNotificationsAPIView(APIView):
    """GET: Единый список уведомлений (неподтвержденные записи + новые отзывы)"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = []

        pending_bookings = Booking.objects.filter(status='pending').order_by('-created_at')
        for b in pending_bookings:
            notifications.append({
                'id': b.id,
                'type': 'booking',
                'title': f'Новая запись: {b.client_name}',
                'body': f'{b.appointment_datetime.strftime("%d.%m %H:%M")} • {b.phone}',
                'created_at': b.created_at,
                'is_read': b.is_read,
            })

        new_reviews = Review.objects.filter(is_active=False).order_by('-created_at')
        for r in new_reviews:
            notifications.append({
                'id': r.id,
                'type': 'review',
                'title': f'Новый отзыв от {r.author_name}',
                'body': f'Оценка: {r.rating}/5 • {r.text[:30]}...',
                'created_at': r.created_at,
                'is_read': r.is_read,
            })

        notifications.sort(key=lambda x: x['created_at'], reverse=True)

        for n in notifications:
            n['created_at'] = n['created_at'].strftime('%d.%m.%Y %H:%M')

        return Response({'notifications': notifications}, status=status.HTTP_200_OK)


class AdminNotificationReadAPIView(APIView):
    """PATCH: Пометить уведомление как прочитанное"""
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        notif_type = request.data.get('type')
        notif_id = request.data.get('id')

        if not notif_type or not notif_id:
            return Response({'error': 'Не переданы type или id'}, status=status.HTTP_400_BAD_REQUEST)

        if notif_type == 'booking':
            obj = get_object_or_404(Booking, pk=notif_id)
        elif notif_type == 'review':
            obj = get_object_or_404(Review, pk=notif_id)
        else:
            return Response({'error': 'Неверный тип'}, status=status.HTTP_400_BAD_REQUEST)

        obj.is_read = True
        obj.save(update_fields=['is_read'])

        return Response({'success': True, 'message': 'Уведомление прочитано'}, status=status.HTTP_200_OK)




class AdminBookingStatusAPIView(APIView):
    """POST: Подтвердить, отменить, завершить или отметить неявку"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        new_status = request.data.get('status')

        if new_status not in ['confirmed', 'cancelled', 'completed', 'no_show']:
            return Response({'error': 'Неверный статус'}, status=status.HTTP_400_BAD_REQUEST)

        old_status = booking.status
        booking.status = new_status

        # Если админ менял услуги при завершении
        services_ids = request.data.get('services_ids')
        if services_ids:
            if isinstance(services_ids, str):
                services_ids = [int(i) for i in services_ids.split(',') if i]
            services = Service.objects.filter(id__in=services_ids, is_active=True)
            booking.services.set(services)

        booking.save()

        # === ЛОГИКА ОТПРАВКИ СМС И НАПОМИНАНИЙ ===

        # 1. ПОДТВЕРЖДЕНИЕ
        if old_status == 'pending' and new_status == 'confirmed':
            async_task('booking_app.tasks.send_event_sms_task', booking.id, 'creation')
            schedule_reminders(booking.id, booking.appointment_datetime)

        # 2. ОТМЕНА
        elif new_status == 'cancelled' and old_status in ['pending', 'confirmed']:
            if booking.client:
                from cabinet_app.services.bonuses import handle_booking_cancelled
                try:
                    handle_booking_cancelled(booking)
                except Exception:
                    logger.exception('handle_booking_cancelled failed for booking %s', booking.pk)
            async_task('booking_app.tasks.send_event_sms_task', booking.id, 'cancel')

        # 2b. НЕЯВКА
        elif new_status == 'no_show' and old_status in ['pending', 'confirmed']:
            if booking.client:
                from cabinet_app.services.bonuses import handle_booking_cancelled
                try:
                    handle_booking_cancelled(booking)
                except Exception:
                    logger.exception('handle_booking_cancelled failed for booking %s (no_show)', booking.pk)

        # 3. ЗАВЕРШЕНИЕ
        elif new_status == 'completed' and old_status != 'completed':
            try:
                with transaction.atomic():
                    locked = Booking.objects.select_for_update().get(pk=booking.pk)

                    if locked.bonuses_processed_at is not None:
                        logger.warning(
                            'booking %s already processed (bonuses_processed_at=%s), skip',
                            booking.pk, locked.bonuses_processed_at,
                        )
                    elif locked.client:
                        client = locked.client
                        client.total_bookings += 1
                        client.total_spent += locked.total_price
                        client.last_visit = locked.appointment_datetime
                        client.save()

                        # Читаем флаг из запроса (админка должна его передать)
                        use_bonuses = request.data.get('use_bonuses', False)
                        if isinstance(use_bonuses, str):
                            use_bonuses = use_bonuses.lower() in ('true', '1', 'yes')

                        from cabinet_app.services.bonuses import apply_bonus_effects
                        # Передаем флаг в функцию, сертификаты она не тронет
                        apply_bonus_effects(locked, use_bonuses=use_bonuses, created_by=request.user)
                        
            except Exception:
                logger.exception('completed flow failed for booking %s', booking.pk)

            # SMS с просьбой об отзыве — вне транзакции
            async_task('booking_app.tasks.send_review_request_task', booking.id)

        return Response({
            'success': True,
            'status': booking.status,
            'message': f'Статус записи изменен на {booking.get_status_display()}'
        }, status=status.HTTP_200_OK)

class AdminClientCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        name = request.data.get('name', '').strip()
        phone = request.data.get('phone', '').strip()
        email = request.data.get('email', '').strip()

        if not phone:
            return Response({'error': 'Телефон обязателен'}, status=status.HTTP_400_BAD_REQUEST)

        from booking_app.utils import get_or_create_client
        client = get_or_create_client(phone, name, email)

        return Response({
            'success': True,
            'client': {
                'id': client.id,
                'name': client.name,
                'phone': client.phone
            }
        }, status=status.HTTP_201_CREATED)


class AdminBlockDayAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BlockDaySerializer(data=request.data)

        if serializer.is_valid():
            target_date = serializer.validated_data['date']
            reason = serializer.validated_data.get('reason', 'Выходной')

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


# ==========================================
# API ДЛЯ CRM (КЛИЕНТЫ)
# ==========================================

class AdminClientDetailAPIView(APIView):
    """GET: Полная информация о клиенте и его история записей"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        client = get_object_or_404(Client, pk=pk)

        bookings = client.bookings.all().order_by('-appointment_datetime')
        history = []
        for b in bookings:
            history.append({
                'id': b.id,
                'date': b.appointment_datetime.strftime('%d.%m.%Y %H:%M'),
                'services': [s.name for s in b.services.all()],
                'total_price': int(b.total_price),
                'status': b.status,
                'status_display': b.get_status_display(),
            })

        data = {
            'id': client.id,
            'name': client.name,
            'phone': client.phone,
            'email': client.email,
            'total_bookings': client.total_bookings,
            'total_spent': int(client.total_spent),
            'notes': client.notes,
            'history': history,
        }

        return Response(data, status=status.HTTP_200_OK)


class AdminClientUpdateNotesAPIView(APIView):
    """PATCH: Сохранить заметки о клиенте"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        notes = request.data.get('notes')

        if notes is not None:
            client.notes = notes
            client.save()
            return Response({'success': True, 'message': 'Заметки сохранены'})

        return Response({'error': 'Нет данных для обновления'}, status=400)


class AdminBookingDetailAPIView(APIView):
    """GET: Получить данные одной записи по ID"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)

        services_data = [{'id': s.id, 'name': s.name} for s in booking.services.all()]

        data = {
            'id': booking.id,
            'client_id': booking.client.id if booking.client else 0,
            'client_name': booking.client_name,
            'phone': booking.phone,
            'status': booking.status,
            'services': services_data,
            'time': booking.appointment_datetime.strftime('%H:%M'),
            'date': booking.appointment_datetime.strftime('%Y-%m-%d'),
            'is_start': True
        }
        return Response(data, status=status.HTTP_200_OK)