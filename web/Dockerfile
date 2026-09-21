# backend/Dockerfile

# 1. Базовый образ (slim версия для меньшего размера)
FROM python:3.13

# 2. Переменные окружения для Python
# PYTHONDONTWRITEBYTECODE: не создавать .pyc файлы (экономит место)
# PYTHONUNBUFFERED: вывод логов в консоль без буферизации (важно для docker logs)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Рабочая директория внутри контейнера
WORKDIR /app

# 4. Установка системных зависимостей
# gcc: для компиляции некоторых python-пакетов
# libpq-dev: для подключения к PostgreSQL (psycopg2)
# libjpeg-dev, zlib1g-dev: для работы с изображениями (Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# 5. Установка Python-зависимостей
# Копируем только requirements.txt сначала, чтобы Docker кэшировал этот слой
COPY requirements.txt /app/
RUN pip install -r requirements.txt

# 6. Копируем весь проект в контейнер
COPY . /app/

# 7. Создаем папки для статики и медиа (если их нет в репозитории)
RUN mkdir -p /app/staticfiles /app/mediafiles

# 8. Копируем и делаем исполняемым скрипт entrypoint
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 9. Открываем порт (для документации, в compose мы его пробрасываем)
EXPOSE 8000

# 10. Указываем entrypoint. 
# Всё, что будет передано в CMD (из docker-compose), подставится вместо "$@"
ENTRYPOINT ["/app/entrypoint.sh"]