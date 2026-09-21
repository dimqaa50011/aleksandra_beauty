#!/bin/bash
# backend/entrypoint.sh

# Останавливать скрипт при любой ошибке
set -e

echo "Ожидание доступности базы данных..."
# Опционально: можно добавить скрипт ожидания БД, если она поднимается долго.

echo "Применение миграций базы данных..."
python manage.py migrate --noinput

echo "Сборка статических файлов..."
python manage.py collectstatic --noinput

echo "Запуск сервера..."
# exec заменяет текущий процесс на gunicorn. 
# Это важно, чтобы gunicorn получал сигналы (например, SIGTERM для graceful shutdown)
exec "$@"