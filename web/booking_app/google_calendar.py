import os
from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import timedelta

# Путь к файлу ключей (лежит в корне проекта, рядом с manage.py)
# BASE_DIR обычно указывает на папку, где лежит manage.py
CREDENTIALS_PATH = os.path.join(settings.BASE_DIR, 'google-credentials.json')
SCOPES = ['https://www.googleapis.com/auth/calendar.events', 'https://www.googleapis.com/auth/calendar']
# beauty_app/google_calendar.py
import os
from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import timedelta

CREDENTIALS_PATH = os.path.join(settings.BASE_DIR, 'google-credentials.json')
SCOPES = ['https://www.googleapis.com/auth/calendar']


import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from django.conf import settings

def get_google_calendar_service():
    """Получает сервис Google Calendar"""
    # Здесь должна быть твоя логика авторизации
    # Пример (адаптируй под свою реализацию):
    creds = Credentials(
        token=settings.GOOGLE_TOKEN,
        refresh_token=settings.GOOGLE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )
    return build('calendar', 'v3', credentials=creds)


def create_or_update_google_event(booking):
    """
    Создаёт новое событие в Google Calendar или обновляет существующее.
    Возвращает event_id.
    """
    try:
        service = get_google_calendar_service()
        
        event_body = {
            'summary': f"{booking.client_name} — {booking.service.name}",
            'description': f"Телефон: {booking.phone}\nEmail: {booking.email or 'не указан'}",
            'start': {
                'dateTime': booking.appointment_datetime.isoformat(),
                'timeZone': 'Europe/Moscow',
            },
            'end': {
                'dateTime': (booking.appointment_datetime + 
                           __import__('datetime').timedelta(minutes=booking.service.duration)).isoformat(),
                'timeZone': 'Europe/Moscow',
            },
        }
        
        calendar_id = "belkasasha1986@gmail.com"

        # Если уже есть google_event_id — обновляем, иначе создаём
        if booking.google_event_id:
            event = service.events().update(
                calendarId=calendar_id,
                eventId=booking.google_event_id,
                body=event_body
            ).execute()
        else:
            event = service.events().insert(
                calendarId=calendar_id,
                body=event_body
            ).execute()

        return event['id']

    except Exception as e:
        print(f"Ошибка работы с Google Calendar: {e}")
        return None

def create_google_calendar_event(booking):
    """Создает событие в Google Календаре и возвращает его ID"""
    
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH, scopes=SCOPES)
    
    service = build('calendar', 'v3', credentials=creds)
    
    duration_minutes = getattr(booking.service, 'duration', 60)
    end_time = booking.appointment_datetime + timedelta(minutes=duration_minutes)
    
    event = {
        'summary': f"💅 {booking.service.name} — {booking.client_name}",
        'description': f"Клиент: {booking.client_name}\nТелефон: {booking.phone}\nEmail: {booking.email or 'Не указан'}\n\nСтудия Sasha Sugar, Спасский пер., 7",
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
            'overrides': [{'method': 'popup', 'minutes': 120}],
        },
    }
    
    # ВАЖНО: Убедись, что здесь именно тот ID, который мы найдем ниже
    CALENDAR_ID = 'belkasasha1986@gmail.com' 
    
    # Этот вызов выбросит ошибку, если что-то не так. Мы её поймаем в signals.py
    created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    
    return created_event.get('id')