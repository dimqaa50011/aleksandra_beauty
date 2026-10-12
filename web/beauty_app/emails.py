# beauty_app/emails.py
from django.core.mail import EmailMessage
from django.conf import settings
import os

def send_booking_confirmation_email(booking):
    """
    Отправляет клиенту письмо с подтверждением записи и сертификатом.
    """
    subject = "🌸 Ваша запись в Sasha Sugar подтверждена!"
    
    # Форматируем дату и время для письма
    date_str = booking.appointment_datetime.strftime('%d.%m.%Y')
    time_str = booking.appointment_datetime.strftime('%H:%M')
    
    # Текст письма (можно сделать HTML-шаблон, но пока сделаем красивый текст)
    message = f"""
    Здравствуйте, {booking.client_name}!

    Спасибо, что выбрали студию Sasha Sugar. Ваша онлайн-запись успешно оформлена.

    📅 Дата: {date_str}
    ⏰ Время: {time_str}
    💅 Услуга: {booking.service.name}
    📍 Адрес: Санкт-Петербург, Спасский переулок, 7

    🎁 В качестве подарка за онлайн-запись, мы подготовили для вас персональный сертификат на скидку 10% на следующий визит! 
    Просто покажите это письмо администратору или назовите промокод: SUGAR10

    Если у вас изменились планы, пожалуйста, предупредите нас не менее чем за 24 часа по телефону или ответным письмом.

    С любовью и заботой о вашей красоте,
    Команда Sasha Sugar
    """

    # Создаем объект письма
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[booking.email],
    )

    # === ЕСЛИ У ТЕБЯ ЕСТЬ ФАЙЛ СЕРТИФИКАТА (PDF или JPG), РАСКОММЕНТИРУЙ ЭТО: ===
    # cert_path = os.path.join(settings.BASE_DIR, 'media', 'certificates', 'sugar_cert.pdf')
    # if os.path.exists(cert_path):
    #     email.attach_file(cert_path)

    try:
        email.send(fail_silently=False)
        return True
    except Exception as e:
        print(f"Ошибка отправки письма: {e}")
        return False