from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime
from booking_app.models import BlockedSlot, Booking, Client, DayOff
from .models import Expense

class AdminStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        today = timezone.localdate()
        now = timezone.now() # <-- Добавили текущее время
        
        if not start_date_str or not end_date_str:
            start_date = today.replace(day=1)
            end_date = today
        else:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        # 1. ПОДСЧЕТ ДНЕЙ
        total_days = (end_date - start_date).days + 1
        day_offs = set(DayOff.objects.filter(date__range=[start_date, end_date]).values_list('date', flat=True))
        full_blocks = set(BlockedSlot.objects.filter(date__range=[start_date, end_date], is_full_day=True).values_list('date', flat=True))
        blocked_dates = day_offs.union(full_blocks)
        blocked_days_count = len(blocked_dates)
        working_days = total_days - blocked_days_count

        # 2. СТАТИСТИКА ПО ЗАПИСЯМ
        bookings = Booking.objects.filter(appointment_datetime__date__range=[start_date, end_date])
        
        total_bookings = bookings.count()
        completed = bookings.filter(status='completed')
        cancelled = bookings.filter(status='cancelled')
        
        # Запланированные: только те, время которых ЕЩЕ НЕ НАСТУПИЛО (и они не отменены)
        scheduled = bookings.filter(
            status__in=['confirmed', 'pending'],
            appointment_datetime__gte=now 
        )
        
        # Неподтвержденные: те, что ждут действия админа
        unconfirmed = bookings.filter(status='pending')

        # 3. ФИНАНСЫ
        revenue = sum(b.total_price for b in completed)
        planned_revenue = sum(b.total_price for b in scheduled)
        
        expenses = Expense.objects.filter(date__range=[start_date, end_date])
        total_expenses = sum(e.amount for e in expenses)
        net_profit = revenue - total_expenses

        # 4. КЛИЕНТЫ
        visited_clients = completed.exclude(client__isnull=True).values('client').distinct().count()
        new_clients = Client.objects.filter(first_visit__date__range=[start_date, end_date]).count()

        return Response({
            'period': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d'),
                'total_days': total_days,
                'working_days': working_days,
                'blocked_days': blocked_days_count,
            },
            'bookings': {
                'total': total_bookings,
                'completed': completed.count(),
                'cancelled': cancelled.count(),
                'scheduled': scheduled.count(),
                'unconfirmed': unconfirmed.count(), # <-- НОВОЕ ПОЛЕ
            },
            'clients': {
                'visited': visited_clients,
                'new': new_clients,
            },
            'finance': {
                'revenue': float(revenue),
                'planned_revenue': float(planned_revenue),
                'expenses': float(total_expenses),
                'net_profit': float(net_profit),
            }
        })



class AdminExpenseAPIView(APIView):
    """GET: Список расходов, POST: Добавить расход"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        
        expenses = Expense.objects.all()
        if start_date_str and end_date_str:
            expenses = expenses.filter(date__range=[start_date_str, end_date_str])

        data = [{
            'id': e.id,
            'amount': float(e.amount),
            'description': e.description,
            'date': e.date.strftime('%d.%m.%Y')
        } for e in expenses]
        
        return Response({'expenses': data})

    def post(self, request):
        amount = request.data.get('amount')
        description = request.data.get('description')
        
        if not amount or not description:
            return Response({'error': 'Укажите сумму и описание'}, status=400)
            
        expense = Expense.objects.create(
            amount=amount, 
            description=description,
            date=timezone.localdate()
        )
        return Response({'success': True, 'id': expense.id}, status=201)

class AdminExpenseDetailAPIView(APIView):
    """PATCH: Обновить расход, DELETE: Удалить расход"""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            expense = Expense.objects.get(pk=pk)
        except Expense.DoesNotExist:
            return Response({'error': 'Расход не найден'}, status=404)

        amount = request.data.get('amount')
        description = request.data.get('description')

        if amount is not None:
            expense.amount = amount
        if description is not None:
            expense.description = description
            
        expense.save()
        return Response({'success': True, 'message': 'Расход обновлен'})

    def delete(self, request, pk):
        try:
            expense = Expense.objects.get(pk=pk)
            expense.delete()
            return Response({'success': True, 'message': 'Расход удален'}, status=200)
        except Expense.DoesNotExist:
            return Response({'error': 'Расход не найден'}, status=404)