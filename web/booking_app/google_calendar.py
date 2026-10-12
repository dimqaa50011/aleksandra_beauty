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
    CALENDAR_ID = 'korendyba5011@gmail.com' 
    
    # Этот вызов выбросит ошибку, если что-то не так. Мы её поймаем в signals.py
    created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
    
    return created_event.get('id')