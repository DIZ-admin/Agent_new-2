# Photo Agent для SharePoint

Автоматическая система обработки и загрузки фотографий в SharePoint с использованием искусственного интеллекта для анализа и обогащения метаданных.

## Функциональность

1. Загрузка схемы метаданных из целевой библиотеки SharePoint
2. Скачивание фотографий из исходной библиотеки SharePoint
3. Анализ фотографий с помощью OpenAI для определения содержимого
4. Генерация метаданных на основе анализа AI и схемы библиотеки
5. Загрузка фотографий с метаданными в целевую библиотеку SharePoint
6. Проверка результатов и формирование отчета
7. Веб-интерфейс для управления всеми процессами и настройками системы

## Структура проекта

```
.
├── config/                  # Конфигурационные файлы
│   ├── config.env           # Переменные окружения
│   ├── prompts/             # Промпты для OpenAI
│   └── sharepoint_choices.json # Схема метаданных SharePoint
├── data/                    # Данные
│   ├── analysis/            # Результаты анализа OpenAI
│   ├── downloads/           # Скачанные фотографии
│   ├── metadata/            # Извлеченные метаданные
│   ├── processed/           # Обработанные фотографии
│   ├── registry/            # Реестр обработанных файлов
│   ├── reports/             # Отчеты о результатах
│   ├── upload/              # Файлы для загрузки
│   │   └── metadata/        # Метаданные для загрузки
│   └── uploaded/            # Загруженные файлы
├── docs/                    # Документация
├── logs/                    # Журналы
├── src/                     # Исходный код
│   ├── utils/               # Утилиты
│   │   ├── config.py        # Управление конфигурацией
│   │   ├── logging.py       # Настройка логирования
│   │   ├── paths.py         # Управление путями
│   │   └── registry.py      # Реестр обработанных файлов
│   ├── web/                 # Веб-интерфейс
│   │   ├── static/          # Статические файлы
│   │   ├── templates/       # Шаблоны
│   │   └── views/           # Обработчики запросов
│   ├── auto_process.py      # Основной скрипт
│   ├── metadata_schema.py   # Получение схемы метаданных
│   ├── photo_metadata.py    # Обработка метаданных фото
│   ├── openai_analyzer.py   # Анализ с OpenAI
│   ├── metadata_generator.py # Генерация метаданных
│   ├── sharepoint_auth.py   # Аутентификация SharePoint
│   ├── sharepoint_uploader.py # Загрузка в SharePoint
│   ├── transfer_verification.py # Проверка результатов
│   └── web_server.py        # Веб-сервер
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
   OPENAI_PROMPT_TYPE=structured_simple
   MODEL_NAME=gpt-4o
   TEMPERATURE=0.1
   IMAGE_DETAIL=high
   ```

### Запуск

1. Запустите приложение с помощью Docker Compose:
   ```
   docker-compose up -d
   ```

2. Откройте веб-интерфейс по адресу:
   ```
   http://localhost:8080
   ```

3. Проверьте логи:
   ```
   docker-compose logs -f
   ```

4. Для запуска отдельного модуля используйте:
   ```
   docker-compose exec agent python -m src.metadata_schema
   ```

## Веб-интерфейс

Веб-интерфейс предоставляет удобный способ управления системой:

1. **Дашборд** - общая статистика и быстрый доступ к основным функциям
2. **Фотографии** - управление фотографиями в системе
   - Вкладка "Загрузки" - фотографии, загруженные из SharePoint
   - Вкладка "Анализ" - результаты анализа фотографий с помощью OpenAI
   - Вкладка "Загрузка" - фотографии, подготовленные для загрузки в SharePoint
   - Вкладка "Загружено" - фотографии, успешно загруженные в SharePoint
3. **Логи** - просмотр и управление логами системы
4. **Процессы** - запуск и мониторинг процессов обработки
5. **Настройки** - настройка системы
   - Настройки SharePoint
   - Настройки OpenAI API
   - Настройки промптов для OpenAI
   - Настройки параметров модели OpenAI
   - Очистка директорий с данными

## Мониторинг и отчеты

- Логи сохраняются в каталоге `logs/`
- Отчеты о результатах загрузки сохраняются в `data/reports/`
- Для проверки состояния системы используйте веб-интерфейс или запустите:
  ```
  docker-compose exec agent python -m src.transfer_verification
  ```

## Обслуживание

### Очистка данных

Для очистки временных данных используйте веб-интерфейс (раздел "Настройки" -> "Очистка данных") или выполните:
```
docker-compose exec agent rm -rf /app/data/downloads/* /app/data/metadata/* /app/data/analysis/* /app/data/upload/*
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

## Дополнительная документация

Более подробная документация доступна в директории `docs/`:

- `README.md` - общая документация
- `web_interface.md` - документация по веб-интерфейсу
- `ERNI_Photo_Processing_Workflow.md` - описание рабочего процесса
- `openai_prompts.md` - документация по промптам OpenAI
