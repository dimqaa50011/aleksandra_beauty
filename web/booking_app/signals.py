from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Booking
from .google_calendar import create_google_calendar_event
import logging
from .views import send_push_notification

logger = logging.getLogger(__name__)



@receiver(post_save, sender=Booking)
def booking_created_notification(sender, instance, created, **kwargs):
    """Отправляет пуш при создании новой записи"""
    if created and instance.status in ['pending', 'confirmed']:
        title = "🔔 Новая запись!"
        body = f"{instance.client_name} — {instance.service.name}\n{instance.appointment_datetime.strftime('%d.%m %H:%M')}"
        send_push_notification(title, body)

@receiver(post_save, sender=Booking)
def sync_booking_to_google_calendar(sender, instance, created, **kwargs):
    """
    Автоматически создает событие в Google Календаре, 
    если запись подтверждена и еще не имеет google_event_id.
    """
    # Проверяем: статус должен быть confirmed, и события еще не должно быть в Google
    if instance.status == 'confirmed' and not instance.google_event_id:
        try:
            event_id = create_google_calendar_event(instance)
            
            # Сохраняем ID, чтобы не создавать дубликаты при последующих обновлениях
            instance.google_event_id = event_id
            # Используем update_fields, чтобы избежать бесконечного цикла сигналов
            Booking.objects.filter(pk=instance.pk).update(google_event_id=event_id)
            
            logger.info(f"✅ Запись {instance.id} успешно добавлена в Google Календарь (Event ID: {event_id})")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении записи {instance.id} в Google Календарь: {e}")