import os
from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import timedelta

# Путь к файлу ключей (лежит в корне проекта, рядом с manage.py)
CREDENTIALS_PATH = os.path.join(settings.BASE_DIR, 'google-credentials.json')
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# ID календаря (если это календарь самого сервисного аккаунта, можно использовать 'primary')
CALENDAR_ID = 'belkasasha1986@gmail.com'


def get_google_calendar_service():
    """Получает авторизованный сервис Google Calendar"""
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH, scopes=SCOPES
    )
    return build('calendar', 'v3', credentials=creds)


def create_or_update_google_event(booking):
    """
    Создаёт новое событие в Google Calendar или обновляет существующее.
    Возвращает event_id (строку) или None в случае ошибки.
    """
    try:
        service = get_google_calendar_service()
        
        # === ИЗМЕНЕНО: Работаем с несколькими услугами (ManyToMany) ===
        services_list = list(booking.services.all())
        
        # Собираем названия услуг через запятую
        services_names = ", ".join([s.name for s in services_list])
        
        # Считаем общую длительность всех услуг (если вдруг duration=None, берем 60 мин по умолчанию)
        total_duration = sum(s.duration for s in services_list if s.duration) or 60
        
        # Вычисляем время окончания записи
        end_time = booking.appointment_datetime + timedelta(minutes=total_duration)

        # Формируем тело события
        event_body = {
            'summary': f"💅 {services_names} — {booking.client_name}",
            'description': (
                f"Клиент: {booking.client_name}\n"
                f"Телефон: {booking.phone}\n"
                f"Email: {booking.email or 'Не указан'}\n\n"
                f"Студия Sasha Sugar, Спасский пер., 7"
            ),
            'start': {
                'dateTime': booking.appointment_datetime.isoformat(),
                'timeZone': 'Europe/Moscow',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'Europe/Moscow',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 120}, # Напоминание за 2 часа
                ],
            },
        }

        # Если уже есть google_event_id — обновляем событие, иначе создаём новое
        if booking.google_event_id:
            event = service.events().update(
                calendarId=CALENDAR_ID,
                eventId=booking.google_event_id,
                body=event_body
            ).execute()
        else:
            event = service.events().insert(
                calendarId=CALENDAR_ID,
                body=event_body
            ).execute()

        return event.get('id')

    except Exception as e:
        print(f"❌ Ошибка работы с Google Calendar: {e}")
        return None


def delete_google_calendar_event(event_id):
    """
    Опционально: удаляет событие из календаря при отмене записи.
    """
    if not event_id:
        return
        
    try:
        service = get_google_calendar_service()
        service.events().delete(
            calendarId=CALENDAR_ID,
            eventId=event_id
        ).execute()
        print(f"✅ Событие {event_id} удалено из Google Calendar")
    except Exception as e:
        print(f"❌ Ошибка удаления события из Google Calendar: {e}")