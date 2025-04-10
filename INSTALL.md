# Инструкция по установке и запуску Photo Agent

## Требования

- Docker и Docker Compose
- Учетные данные SharePoint
- API-ключ OpenAI

## Шаги по установке

### 1. Клонирование или копирование проекта

Убедитесь, что у вас есть вся структура проекта:

```
.
├── config/
│   ├── config.env
│   └── sharepoint_choices.json (опционально, будет создан при первом запуске)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── run.sh (для Linux/Mac)
├── run.bat (для Windows)
└── src/ (директория с исходным кодом)
```

### 2. Настройка конфигурации

1. Откройте файл `config/config.env` и заполните все необходимые параметры:

```
# SharePoint connection settings
SHAREPOINT_SITE_URL=https://erni.sharepoint.com/sites/100_Testing_KI-Projekte
SHAREPOINT_USERNAME=test.ki@erni-gruppe.ch
SHAREPOINT_PASSWORD=your-password

# Library settings
SOURCE_LIBRARY_TITLE=PhotoLibrary
SHAREPOINT_LIBRARY=Fertige Referenzfotos

# File settings
METADATA_SCHEMA_FILE=config/sharepoint_choices.json
TARGET_FILENAME_MASK=Erni_Referenzfoto_{number}
# Максимальный размер файла в байтах (15MB)
MAX_FILE_SIZE=15728640

# Connection settings
MAX_CONNECTION_ATTEMPTS=3
CONNECTION_RETRY_DELAY=5

# OpenAI settings
OPENAI_API_KEY=your-openai-api-key
OPENAI_CONCURRENCY_LIMIT=5
MAX_TOKENS=1000

# Logging settings
LOG_LEVEL=INFO
LOG_FILE=sharepoint_connector.log

# --- OpenAI Prompt ---
OPENAI_PROMPT_ROLE="Agieren Sie als erfahrener Experte in der Herstellung und dem Bau von Holzhäusern und -konstruktionen."

# другие настройки промпта...
```

### 3. Сборка Docker-образа

Соберите Docker-образ с помощью команды:

#### Linux/Mac:
```bash
./run.sh build
```

#### Windows:
```cmd
run.bat build
```

Или вручную:
```
docker-compose build
```

## Запуск приложения

### Запуск полного процесса

Чтобы запустить полный процесс обработки фотографий:

#### Linux/Mac:
```bash
./run.sh start
```

#### Windows:
```cmd
run.bat start
```

Или вручную:
```
docker-compose up -d
```

### Запуск отдельных модулей

Для запуска только конкретных этапов обработки используйте соответствующие команды:

1. Получение схемы метаданных:
   ```
   ./run.sh schema
   ```

2. Скачивание фотографий:
   ```
   ./run.sh photos
   ```

3. Анализ с помощью OpenAI:
   ```
   ./run.sh analyze
   ```

4. Генерация метаданных:
   ```
   ./run.sh metadata
   ```

5. Загрузка в SharePoint:
   ```
   ./run.sh upload
   ```

6. Проверка результатов:
   ```
   ./run.sh verify
   ```

### Просмотр логов

Для просмотра логов работы системы:

```
./run.sh logs
```

## Проверка работоспособности

Для проверки соединения с SharePoint и OpenAI API запустите:

```
docker-compose run --rm agent python test_connection.py
```

## Обслуживание

### Очистка временных данных

Для очистки временных данных:

```
./run.sh clean-data
```

### Остановка приложения

Для остановки приложения:

```
./run.sh stop
```

## Структура каталогов

После запуска будут созданы следующие каталоги:

- `data/downloads/` - скачанные фотографии
- `data/metadata/` - извлеченные метаданные
- `data/analysis/` - результаты анализа OpenAI
- `data/upload/` - файлы для загрузки
- `data/uploaded/` - загруженные файлы
- `data/reports/` - отчеты о результатах
- `data/registry/` - реестр обработанных файлов
- `logs/` - журналы работы приложения

## Устранение неполадок

Если у вас возникли проблемы:

1. Проверьте подключение к SharePoint и OpenAI API с помощью скрипта `test_connection.py`
2. Проверьте логи в директории `logs/`
3. Убедитесь, что все переменные окружения в `config.env` заполнены корректно
4. Проверьте права доступа к SharePoint-библиотекам

Если проблемы не устраняются, обратитесь к разработчикам.
