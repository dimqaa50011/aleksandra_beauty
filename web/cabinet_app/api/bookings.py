from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from booking_app.models import Booking

from ..serializers.bookings import (
    BookingCancelSerializer,
    BookingCreateSerializer,
    BookingDetailSerializer,
    BookingListSerializer,
    BookingRescheduleSerializer,
)
from ..services import bookings as booking_service
from .base import CabinetAPIView
from django.utils import timezone

class AppointmentListCreateView(CabinetAPIView):
    def get(self, request):
        client = request.user.client
        qs = Booking.objects.filter(client=client).prefetch_related('services')

        now = timezone.now()
        upcoming = qs.filter(
            appointment_datetime__gte=now,
            status__in=['pending', 'confirmed'],
        ).order_by('appointment_datetime')
        past = qs.exclude(
            id__in=upcoming.values('id'),
        ).order_by('-appointment_datetime')[:50]

        return Response({
            'upcoming': BookingListSerializer(upcoming, many=True).data,
            'past': BookingListSerializer(past, many=True).data,
        })

    def post(self, request):
        ser = BookingCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        booking = booking_service.create_appointment(
            user=request.user,
            service_ids=data['service_ids'],
            appointment_datetime=data['appointment_datetime'],
            use_bonuses=data.get('use_bonuses', False),
            bonuses_to_apply=data.get('bonuses_to_apply', 0),
            certificate_id=data.get('certificate_id'),
        )
        return Response(
            BookingDetailSerializer(booking).data,
            status=status.HTTP_201_CREATED,
        )


class AppointmentDetailView(CabinetAPIView):
    def _get(self, request, pk):
        booking = Booking.objects.filter(pk=pk, client=request.user.client).first()
        if booking is None:
            raise NotFound()
        return booking

    def get(self, request, pk):
        return Response(BookingDetailSerializer(self._get(request, pk)).data)

    def delete(self, request, pk):
        booking = self._get(request, pk)
        ser = BookingCancelSerializer(data=request.query_params)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        booking = booking_service.cancel_appointment(
            booking=booking,
            reason=data['reason'],
            reason_text=data.get('reason_text', ''),
        )
        return Response(BookingDetailSerializer(booking).data)


class AppointmentRescheduleView(CabinetAPIView):
    def post(self, request, pk):
        booking = Booking.objects.filter(pk=pk, client=request.user.client).first()
        if booking is None:
            raise NotFound()

        ser = BookingRescheduleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        booking = booking_service.reschedule_appointment(
            booking=booking,
            new_datetime=ser.validated_data['new_datetime'],
        )
        return Response(BookingDetailSerializer(booking).data)