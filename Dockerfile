FROM python:3.9-slim

# Установка рабочей директории
WORKDIR /app

# Копирование файлов проекта
COPY requirements.txt .
COPY src/ /app/src/
COPY config/ /app/config/

# Создание необходимых директорий
RUN mkdir -p /app/data/downloads \
    /app/data/metadata \
    /app/data/analysis \
    /app/data/upload \
    /app/data/upload/metadata \
    /app/data/uploaded \
    /app/data/reports \
    /app/data/registry \
    /app/logs

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Переменные среды
ENV PYTHONPATH="/app:${PYTHONPATH}"
ENV TZ=Europe/Berlin
ENV PYTHONUNBUFFERED=1

# Запуск приложения
CMD ["python", "-m", "src.auto_process"]
