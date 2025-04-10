#!/bin/bash
# Скрипт для запуска и управления контейнером

# Вывод сообщений с цветом
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

function show_help {
    echo -e "${GREEN}Скрипт для управления Photo Agent${NC}"
    echo ""
    echo "Использование:"
    echo "  ./run.sh [команда]"
    echo ""
    echo "Команды:"
    echo "  start       - Запустить контейнер"
    echo "  stop        - Остановить контейнер"
    echo "  restart     - Перезапустить контейнер"
    echo "  logs        - Показать логи"
    echo "  status      - Показать статус контейнера"
    echo "  schema      - Запустить только получение схемы метаданных"
    echo "  photos      - Запустить только скачивание фотографий"
    echo "  analyze     - Запустить только анализ с помощью OpenAI"
    echo "  metadata    - Запустить только генерацию метаданных"
    echo "  upload      - Запустить только загрузку в SharePoint"
    echo "  verify      - Проверить результаты загрузки"
    echo "  build       - Собрать образ"
    echo "  clean-data  - Очистить временные данные"
    echo "  help        - Показать эту справку"
    echo ""
}

# Проверка наличия Docker
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Ошибка: Docker Compose не установлен${NC}"
    exit 1
fi

case "$1" in
    start)
        echo -e "${GREEN}Запуск контейнера...${NC}"
        docker-compose up -d
        ;;
    stop)
        echo -e "${YELLOW}Остановка контейнера...${NC}"
        docker-compose down
        ;;
    restart)
        echo -e "${YELLOW}Перезапуск контейнера...${NC}"
        docker-compose down
        docker-compose up -d
        ;;
    logs)
        echo -e "${GREEN}Просмотр логов (Ctrl+C для выхода)...${NC}"
        docker-compose logs -f
        ;;
    status)
        echo -e "${GREEN}Статус контейнера:${NC}"
        docker-compose ps
        ;;
    schema)
        echo -e "${GREEN}Запуск получения схемы метаданных...${NC}"
        docker-compose run --rm agent python -m src.metadata_schema
        ;;
    photos)
        echo -e "${GREEN}Запуск скачивания фотографий...${NC}"
        docker-compose run --rm agent python -m src.photo_metadata
        ;;
    analyze)
        echo -e "${GREEN}Запуск анализа с помощью OpenAI...${NC}"
        docker-compose run --rm agent python -m src.openai_analyzer
        ;;
    metadata)
        echo -e "${GREEN}Запуск генерации метаданных...${NC}"
        docker-compose run --rm agent python -m src.metadata_generator
        ;;
    upload)
        echo -e "${GREEN}Запуск загрузки в SharePoint...${NC}"
        docker-compose run --rm agent python -m src.sharepoint_uploader
        ;;
    verify)
        echo -e "${GREEN}Проверка результатов загрузки...${NC}"
        docker-compose run --rm agent python -m src.transfer_verification
        ;;
    build)
        echo -e "${GREEN}Сборка образа...${NC}"
        docker-compose build --no-cache
        ;;
    clean-data)
        echo -e "${YELLOW}Очистка временных данных...${NC}"
        docker-compose run --rm agent sh -c "rm -rf /app/data/downloads/* /app/data/metadata/* /app/data/analysis/* /app/data/upload/*"
        echo -e "${GREEN}Данные очищены${NC}"
        ;;
    help|*)
        show_help
        ;;
esac
