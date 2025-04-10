@echo off
REM Скрипт для запуска интеграционных тестов в Windows

setlocal enabledelayedexpansion

REM Проверяем, что мы в корневой директории проекта
if not exist src\. (
    echo Ошибка: Запустите скрипт из корневой директории проекта
    exit /b 1
)

REM Создаем виртуальное окружение для тестов, если оно не существует
if not exist venv\. (
    echo Создание виртуального окружения...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    pip install pytest pytest-mock
) else (
    call venv\Scripts\activate.bat
)

REM Переменные для отслеживания результатов тестов
set UNIT_SUCCESS=0
set DOCKER_SUCCESS=0

REM Проверяем аргументы
if "%~1"=="unit" (
    call :run_unit_tests
    set UNIT_SUCCESS=!ERRORLEVEL!
    set DOCKER_SUCCESS=2
) else if "%~1"=="docker" (
    call :run_docker_tests
    set DOCKER_SUCCESS=!ERRORLEVEL!
    set UNIT_SUCCESS=2
) else (
    call :run_unit_tests
    set UNIT_SUCCESS=!ERRORLEVEL!
    
    call :run_docker_tests
    set DOCKER_SUCCESS=!ERRORLEVEL!
)

REM Выводим итоговый результат
echo.
echo === Результаты тестирования ===
if !UNIT_SUCCESS! EQU 0 (
    echo [OK] Модульные тесты: УСПЕШНО
) else if !UNIT_SUCCESS! EQU 1 (
    echo [FAIL] Модульные тесты: НЕ ПРОЙДЕНЫ
) else (
    echo [SKIP] Модульные тесты: ПРОПУЩЕНЫ
)

if !DOCKER_SUCCESS! EQU 0 (
    echo [OK] Тесты Docker: УСПЕШНО
) else if !DOCKER_SUCCESS! EQU 1 (
    echo [FAIL] Тесты Docker: НЕ ПРОЙДЕНЫ
) else (
    echo [SKIP] Тесты Docker: ПРОПУЩЕНЫ
)

REM Возвращаем общий результат
if !UNIT_SUCCESS! NEQ 0 set ERROR_FLAG=1
if !DOCKER_SUCCESS! NEQ 0 set ERROR_FLAG=1

exit /b !ERROR_FLAG!

:run_unit_tests
echo.
echo Запуск модульных тестов...
python -m unittest discover -s tests -p "test_integration.py"
if %ERRORLEVEL% NEQ 0 (
    echo Модульные тесты не пройдены!
    exit /b 1
) else (
    echo Модульные тесты успешно пройдены!
    exit /b 0
)

:run_docker_tests
echo.
echo Запуск тестов Docker-контейнера...

REM Проверяем, установлен ли Docker
docker-compose --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Ошибка: Docker Compose не установлен
    exit /b 1
)

REM Запускаем тесты Docker
python -m unittest tests\test_docker.py
if %ERRORLEVEL% NEQ 0 (
    echo Тесты Docker-контейнера не пройдены!
    exit /b 1
) else (
    echo Тесты Docker-контейнера успешно пройдены!
    exit /b 0
)
