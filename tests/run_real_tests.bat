@echo off
REM Скрипт для запуска интеграционных тестов с реальными зависимостями в Windows

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

REM Проверяем существование конфигурационного файла
if not exist config\config.env (
    echo Ошибка: Файл config\config.env не найден. Он необходим для тестов с реальными зависимостями.
    exit /b 1
)

REM Проверка подключений перед тестами
echo.
echo Проверка подключений перед запуском тестов...

python -c "import sys; sys.path.append('.'); from src.sharepoint_auth import test_connection; sp_ok = test_connection(); print('SharePoint connection: ' + ('OK' if sp_ok else 'FAILED')); sys.exit(0 if sp_ok else 1)"
if %ERRORLEVEL% NEQ 0 (
    echo Ошибка: Не удалось подключиться к SharePoint. Проверьте учетные данные.
    exit /b 1
)

python -c "import sys; sys.path.append('.'); from src.utils.config import get_config; import openai; config = get_config(); openai.api_key = config.openai.api_key; try: response = openai.chat.completions.create(model='gpt-4o', messages=[{'role': 'system', 'content': 'You are a helpful assistant.'}, {'role': 'user', 'content': 'Hello, test'}], max_tokens=5); print('OpenAI connection: OK'); except Exception as e: print(f'OpenAI connection FAILED: {e}'); sys.exit(1)"
if %ERRORLEVEL% NEQ 0 (
    echo Ошибка: Не удалось подключиться к OpenAI API. Проверьте API-ключ.
    exit /b 1
)

echo Проверка подключений успешно пройдена!

REM Переменные для отслеживания результатов тестов
set INT_SUCCESS=0
set DOCKER_SUCCESS=0

REM Проверяем аргументы
if "%~1"=="integration" (
    call :run_integration_tests
    set INT_SUCCESS=!ERRORLEVEL!
    set DOCKER_SUCCESS=2
) else if "%~1"=="docker" (
    call :run_docker_tests
    set DOCKER_SUCCESS=!ERRORLEVEL!
    set INT_SUCCESS=2
) else (
    call :run_integration_tests
    set INT_SUCCESS=!ERRORLEVEL!
    
    call :run_docker_tests
    set DOCKER_SUCCESS=!ERRORLEVEL!
)

REM Очистка после тестов
call :cleanup

REM Выводим итоговый результат
echo.
echo === Результаты тестирования с реальными зависимостями ===
if !INT_SUCCESS! EQU 0 (
    echo [OK] Интеграционные тесты: УСПЕШНО
) else if !INT_SUCCESS! EQU 1 (
    echo [FAIL] Интеграционные тесты: НЕ ПРОЙДЕНЫ
) else (
    echo [SKIP] Интеграционные тесты: ПРОПУЩЕНЫ
)

if !DOCKER_SUCCESS! EQU 0 (
    echo [OK] Docker-тесты: УСПЕШНО
) else if !DOCKER_SUCCESS! EQU 1 (
    echo [FAIL] Docker-тесты: НЕ ПРОЙДЕНЫ
) else (
    echo [SKIP] Docker-тесты: ПРОПУЩЕНЫ
)

REM Возвращаем общий результат
set ERROR_FLAG=0
if !INT_SUCCESS! EQU 1 set ERROR_FLAG=1
if !DOCKER_SUCCESS! EQU 1 set ERROR_FLAG=1

exit /b !ERROR_FLAG!

:run_integration_tests
echo.
echo Запуск интеграционных тестов с реальными зависимостями...
python -m unittest tests\test_real_integration.py
if %ERRORLEVEL% NEQ 0 (
    echo Интеграционные тесты не пройдены!
    exit /b 1
) else (
    echo Интеграционные тесты успешно пройдены!
    exit /b 0
)

:run_docker_tests
echo.
echo Запуск Docker-тестов с реальными зависимостями...

REM Проверяем, установлен ли Docker
docker-compose --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Ошибка: Docker Compose не установлен
    exit /b 1
)

REM Запускаем тесты Docker
python -m unittest tests\test_real_docker.py
if %ERRORLEVEL% NEQ 0 (
    echo Docker-тесты не пройдены!
    exit /b 1
) else (
    echo Docker-тесты успешно пройдены!
    exit /b 0
)

:cleanup
echo.
echo Очистка тестовой среды...
set /p CLEAN="Удалить тестовые данные? (y/n): "
if /i "%CLEAN%"=="y" (
    if exist real_docker_test (
        rmdir /s /q real_docker_test
        echo Каталог real_docker_test удален
    )
    
    echo Очистка временных данных...
    if exist data\downloads\*.* del /q data\downloads\*.*
    if exist data\metadata\*.* del /q data\metadata\*.*
    if exist data\analysis\*.* del /q data\analysis\*.*
    if exist data\upload\*.* del /q data\upload\*.*
    echo Временные данные очищены
) else (
    echo Тестовые данные сохранены для анализа
)
exit /b 0
