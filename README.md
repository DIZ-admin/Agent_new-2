# Photo Agent для SharePoint

Автоматическая система обработки и загрузки фотографий в SharePoint с использованием искусственного интеллекта для анализа и обогащения метаданных.

## Функциональность

1. Загрузка схемы метаданных из целевой библиотеки SharePoint
2. Скачивание фотографий из исходной библиотеки SharePoint
3. Анализ фотографий с помощью OpenAI для определения содержимого
4. Генерация метаданных на основе анализа AI и схемы библиотеки
5. Загрузка фотографий с метаданными в целевую библиотеку SharePoint
6. Проверка результатов и формирование отчета

## Структура проекта

```
.
├── config/                  # Конфигурационные файлы
│   ├── config.env           # Переменные окружения
│   └── sharepoint_choices.json # Схема метаданных SharePoint
├── data/                    # Данные
│   ├── analysis/            # Результаты анализа OpenAI
│   ├── downloads/           # Скачанные фотографии
│   ├── metadata/            # Извлеченные метаданные
│   ├── registry/            # Реестр обработанных файлов
│   ├── reports/             # Отчеты о результатах
│   ├── upload/              # Файлы для загрузки
│   └── uploaded/            # Загруженные файлы
├── logs/                    # Журналы
├── src/                     # Исходный код
│   ├── utils/               # Утилиты
│   │   ├── config.py        # Управление конфигурацией
│   │   ├── logging.py       # Настройка логирования
│   │   ├── paths.py         # Управление путями
│   │   └── registry.py      # Реестр обработанных файлов
│   ├── auto_process.py      # Основной скрипт
│   ├── metadata_schema.py   # Получение схемы метаданных
│   ├── photo_metadata.py    # Обработка метаданных фото
│   ├── openai_analyzer.py   # Анализ с OpenAI
│   ├── metadata_generator.py # Генерация метаданных
│   ├── sharepoint_auth.py   # Аутентификация SharePoint
│   ├── sharepoint_uploader.py # Загрузка в SharePoint
│   └── transfer_verification.py # Проверка результатов
├── Dockerfile               # Dockerfile для сборки образа
├── docker-compose.yml       # Docker Compose конфигурация
├── requirements.txt         # Зависимости Python
└── README.md                # Документация
```

## Запуск в Docker

### Предварительные требования

- Docker и Docker Compose
- Учетные данные SharePoint
- API-ключ OpenAI

### Подготовка

1. Создайте или отредактируйте файл `config/config.env` с вашими параметрами:
   ```
   # SharePoint connection settings
   SHAREPOINT_SITE_URL=https://your-sharepoint.com/sites/your-site
   SHAREPOINT_USERNAME=your.username@example.com
   SHAREPOINT_PASSWORD=your-password
   
   # Library settings
   SOURCE_LIBRARY_TITLE=SourceLibrary
   SHAREPOINT_LIBRARY=TargetLibrary
   
   # OpenAI settings
   OPENAI_API_KEY=your-openai-api-key
   ```

### Запуск

1. Запустите приложение с помощью Docker Compose:
   ```
   docker-compose up -d
   ```

2. Проверьте логи:
   ```
   docker-compose logs -f
   ```

3. Для запуска отдельного модуля используйте:
   ```
   docker-compose run agent python -m src.metadata_schema
   ```

## Мониторинг и отчеты

- Логи сохраняются в каталоге `logs/`
- Отчеты о результатах загрузки сохраняются в `data/reports/`
- Для проверки состояния системы запустите:
  ```
  docker-compose run agent python -m src.transfer_verification
  ```

## Обслуживание

### Очистка данных

Для очистки временных данных выполните:
```
docker-compose run agent rm -rf /app/data/downloads/* /app/data/metadata/* /app/data/analysis/* /app/data/upload/*
```

### Обновление

1. Остановите контейнер:
   ```
   docker-compose down
   ```

2. Пересоберите образ:
   ```
   docker-compose build --no-cache
   ```

3. Запустите обновленный контейнер:
   ```
   docker-compose up -d
   ```
