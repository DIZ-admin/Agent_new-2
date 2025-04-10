@echo off
REM Скрипт для запуска и управления контейнером в Windows

setlocal enabledelayedexpansion

IF "%~1"=="" GOTO help

IF "%~1"=="start" (
    echo Запуск контейнера...
    docker-compose up -d
    GOTO end
)

IF "%~1"=="stop" (
    echo Остановка контейнера...
    docker-compose down
    GOTO end
)

IF "%~1"=="restart" (
    echo Перезапуск контейнера...
    docker-compose down
    docker-compose up -d
    GOTO end
)

IF "%~1"=="logs" (
    echo Просмотр логов (Ctrl+C для выхода)...
    docker-compose logs -f
    GOTO end
)

IF "%~1"=="status" (
    echo Статус контейнера:
    docker-compose ps
    GOTO end
)

IF "%~1"=="schema" (
    echo Запуск получения схемы метаданных...
    docker-compose run --rm agent python -m src.metadata_schema
    GOTO end
)

IF "%~1"=="photos" (
    echo Запуск скачивания фотографий...
    docker-compose run --rm agent python -m src.photo_metadata
    GOTO end
)

IF "%~1"=="analyze" (
    echo Запуск анализа с помощью OpenAI...
    docker-compose run --rm agent python -m src.openai_analyzer
    GOTO end
)

IF "%~1"=="metadata" (
    echo Запуск генерации метаданных...
    docker-compose run --rm agent python -m src.metadata_generator
    GOTO end
)

IF "%~1"=="upload" (
    echo Запуск загрузки в SharePoint...
    docker-compose run --rm agent python -m src.sharepoint_uploader
    GOTO end
)

IF "%~1"=="verify" (
    echo Проверка результатов загрузки...
    docker-compose run --rm agent python -m src.transfer_verification
    GOTO end
)

IF "%~1"=="build" (
    echo Сборка образа...
    docker-compose build --no-cache
    GOTO end
)

IF "%~1"=="clean-data" (
    echo Очистка временных данных...
    docker-compose run --rm agent sh -c "rm -rf /app/data/downloads/* /app/data/metadata/* /app/data/analysis/* /app/data/upload/*"
    echo Данные очищены
    GOTO end
)

:help
echo Скрипт для управления Photo Agent
echo.
echo Использование:
echo   run.bat [команда]
echo.
echo Команды:
echo   start       - Запустить контейнер
echo   stop        - Остановить контейнер
echo   restart     - Перезапустить контейнер
echo   logs        - Показать логи
echo   status      - Показать статус контейнера
echo   schema      - Запустить только получение схемы метаданных
echo   photos      - Запустить только скачивание фотографий
echo   analyze     - Запустить только анализ с помощью OpenAI
echo   metadata    - Запустить только генерацию метаданных
echo   upload      - Запустить только загрузку в SharePoint
echo   verify      - Проверить результаты загрузки
echo   build       - Собрать образ
echo   clean-data  - Очистить временные данные
echo   help        - Показать эту справку
echo.

:end
endlocal
