from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Booking
# === ИЗМЕНЕНО: Импортируем новую функцию ===
from .google_calendar import create_or_update_google_event, delete_google_calendar_event


@receiver(post_save, sender=Booking)
def sync_booking_to_google_calendar(sender, instance, created, **kwargs):
    """
    Автоматически создает или обновляет событие в Google Calendar 
    при сохранении записи (если статус не 'cancelled')
    """
    if instance.status in ['confirmed', 'pending']:
        # Вызываем новую функцию
        event_id = create_or_update_google_event(instance)
        
        if event_id and not instance.google_event_id:
            # Если событие создано впервые, сохраняем его ID в базу.
            # Используем .update(), чтобы не вызвать бесконечный цикл post_save сигналов!
            Booking.objects.filter(pk=instance.pk).update(google_event_id=event_id)


@receiver(post_delete, sender=Booking)
def delete_booking_from_google_calendar(sender, instance, **kwargs):
    """
    Автоматически удаляет событие из Google Calendar при удалении записи
    """
    if instance.google_event_id:
        delete_google_calendar_event(instance.google_event_id)