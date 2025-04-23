# Локальная установка Photo Agent

Это руководство описывает процесс локальной установки и запуска Photo Agent в контейнере Docker без необходимости настройки реальных учетных данных SharePoint и API-ключей OpenAI.

## Требования

- Docker и Docker Compose
- Bash (для Linux/Mac) или Git Bash/WSL (для Windows)

## Быстрая установка

1. Запустите скрипт настройки:

```bash
chmod +x setup-local.sh
./setup-local.sh
```

2. Запустите контейнер:

```bash
docker-compose -f docker-compose.local.yml up
```

3. Откройте веб-интерфейс по адресу:
```
http://localhost:8080
```

## Ручная установка

Если вы предпочитаете выполнить установку вручную, следуйте этим шагам:

1. Создайте необходимые директории:

```bash
mkdir -p data/downloads data/metadata data/analysis data/upload/metadata data/uploaded data/reports data/registry data/processed logs
```

2. Соберите Docker-образ:

```bash
docker-compose -f docker-compose.local.yml build
```

3. Запустите контейнер:

```bash
docker-compose -f docker-compose.local.yml up
```

## Режим локальной разработки

В локальном режиме:

- SharePoint API эмулируется (не требуются реальные учетные данные)
- OpenAI API эмулируется (не требуется реальный API-ключ)
- Веб-интерфейс доступен на порту 8080
- Все данные сохраняются в локальных директориях

## Использование реальных сервисов

Если вы хотите использовать реальные сервисы SharePoint и OpenAI:

1. Отредактируйте файл `config/config.local.env`:
   - Установите `MOCK_SHAREPOINT=false`
   - Установите `MOCK_OPENAI=false`
   - Укажите реальные учетные данные SharePoint и API-ключ OpenAI

2. Перезапустите контейнер:

```bash
docker-compose -f docker-compose.local.yml down
docker-compose -f docker-compose.local.yml up
```

## Структура проекта

- `config/config.local.env` - локальная конфигурация
- `docker-compose.local.yml` - конфигурация Docker для локальной разработки
- `data/` - директории для хранения данных
- `logs/` - журналы работы приложения

## Доступные команды

Вы можете запустить отдельные модули системы, изменив команду в `docker-compose.local.yml`:

```yaml
# Веб-интерфейс (по умолчанию)
command: python -m src.web_server

# Полный процесс обработки
command: python -m src.auto_process

# Получение схемы метаданных
command: python -m src.metadata_schema

# Обработка фотографий
command: python -m src.photo_metadata

# Анализ с помощью OpenAI
command: python -m src.openai_analyzer

# Генерация метаданных
command: python -m src.metadata_generator
```

## Устранение неполадок

### Проблемы с Docker

Если у вас возникли проблемы с Docker:

```bash
# Остановить все контейнеры
docker-compose -f docker-compose.local.yml down

# Удалить все образы и контейнеры
docker system prune -a

# Повторить установку
./setup-local.sh
```

### Проблемы с доступом к файлам

Если возникают проблемы с правами доступа к файлам:

```bash
# Установить правильные разрешения
chmod -R 755 data logs
```

## Дополнительная информация

Для получения дополнительной информации о проекте обратитесь к основной документации в файле `README.md`.
