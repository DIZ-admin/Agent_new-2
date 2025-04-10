#!/bin/bash
# Скрипт для запуска интеграционных тестов с реальными зависимостями

# Вывод сообщений с цветом
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Проверяем, что мы в корневой директории проекта
if [ ! -d "src" ] || [ ! -d "config" ]; then
    echo -e "${RED}Ошибка: Запустите скрипт из корневой директории проекта${NC}"
    exit 1
fi

# Создаем виртуальное окружение для тестов, если оно не существует
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Создание виртуального окружения...${NC}"
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    pip install pytest pytest-mock
else
    source venv/bin/activate
fi

# Проверяем существование конфигурационного файла
if [ ! -f "config/config.env" ]; then
    echo -e "${RED}Ошибка: Файл config/config.env не найден. Он необходим для тестов с реальными зависимостями.${NC}"
    exit 1
fi

# Функция для проверки подключений перед тестами
check_connections() {
    echo -e "\n${GREEN}Проверка подключений перед запуском тестов...${NC}"
    
    python -c "
import sys
sys.path.append('.')
from src.sharepoint_auth import test_connection
from src.utils.config import get_config
import openai

# Test SharePoint
sp_ok = test_connection()
if not sp_ok:
    print('SharePoint connection failed')
    sys.exit(1)
print('SharePoint connection OK')

# Test OpenAI
try:
    config = get_config()
    openai.api_key = config.openai.api_key
    response = openai.chat.completions.create(
        model='gpt-4o',
        messages=[
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': 'Hello, test'}
        ],
        max_tokens=5
    )
    print('OpenAI connection OK')
except Exception as e:
    print(f'OpenAI connection failed: {e}')
    sys.exit(1)
"
    
    CONNECTION_RESULT=$?
    if [ $CONNECTION_RESULT -ne 0 ]; then
        echo -e "${RED}Проверка подключений не пройдена! Убедитесь, что учетные данные верны.${NC}"
        return 1
    else
        echo -e "${GREEN}Проверка подключений успешно пройдена!${NC}"
        return 0
    fi
}

# Функция для запуска тестов с реальными зависимостями
run_real_integration_tests() {
    echo -e "\n${GREEN}Запуск тестов с реальными зависимостями...${NC}"
    python -m unittest tests/test_real_integration.py
    
    TEST_RESULT=$?
    if [ $TEST_RESULT -ne 0 ]; then
        echo -e "${RED}Тесты с реальными зависимостями не пройдены!${NC}"
        return 1
    else
        echo -e "${GREEN}Тесты с реальными зависимостями успешно пройдены!${NC}"
        return 0
    fi
}

# Функция для запуска Docker-тестов с реальными зависимостями
run_real_docker_tests() {
    echo -e "\n${GREEN}Запуск Docker-тестов с реальными зависимостями...${NC}"
    
    # Проверяем, установлен ли Docker
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Ошибка: Docker Compose не установлен${NC}"
        return 1
    fi
    
    # Запускаем тесты Docker
    python -m unittest tests/test_real_docker.py
    
    TEST_RESULT=$?
    if [ $TEST_RESULT -ne 0 ]; then
        echo -e "${RED}Docker-тесты с реальными зависимостями не пройдены!${NC}"
        return 1
    else
        echo -e "${GREEN}Docker-тесты с реальными зависимостями успешно пройдены!${NC}"
        return 0
    fi
}

# Функция для уборки после тестов
cleanup() {
    echo -e "\n${YELLOW}Очистка тестовой среды...${NC}"
    
    # Спросить пользователя, хочет ли он сохранить данные тестов
    read -p "Удалить тестовые данные? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -d "real_docker_test" ]; then
            rm -rf real_docker_test
            echo -e "${GREEN}Каталог real_docker_test удален${NC}"
        fi
        
        # Очистить данные в папке data
        echo -e "${YELLOW}Очистка временных данных...${NC}"
        find data/downloads -type f -delete 2>/dev/null
        find data/metadata -type f -delete 2>/dev/null
        find data/analysis -type f -delete 2>/dev/null
        find data/upload -type f -delete 2>/dev/null
        echo -e "${GREEN}Временные данные очищены${NC}"
    else
        echo -e "${YELLOW}Тестовые данные сохранены для анализа${NC}"
    fi
}

# Основная функция
main() {
    local INT_SUCCESS=0
    local DOCKER_SUCCESS=0
    
    # Проверяем подключения
    check_connections
    if [ $? -ne 0 ]; then
        echo -e "${RED}Тесты не будут запущены из-за проблем с подключениями.${NC}"
        exit 1
    fi
    
    # Проверяем аргументы
    if [ "$1" == "integration" ]; then
        run_real_integration_tests
        INT_SUCCESS=$?
        DOCKER_SUCCESS=2  # Пропускаем Docker-тесты
    elif [ "$1" == "docker" ]; then
        run_real_docker_tests
        DOCKER_SUCCESS=$?
        INT_SUCCESS=2  # Пропускаем обычные тесты
    else
        # Запускаем все тесты
        run_real_integration_tests
        INT_SUCCESS=$?
        
        run_real_docker_tests
        DOCKER_SUCCESS=$?
    fi
    
    # Очистка после тестов
    cleanup
    
    # Выводим итоговый результат
    echo -e "\n${GREEN}=== Результаты тестирования с реальными зависимостями ===${NC}"
    if [ $INT_SUCCESS -eq 0 ]; then
        echo -e "${GREEN}✓ Интеграционные тесты: УСПЕШНО${NC}"
    elif [ $INT_SUCCESS -eq 1 ]; then
        echo -e "${RED}✗ Интеграционные тесты: НЕ ПРОЙДЕНЫ${NC}"
    else
        echo -e "${YELLOW}- Интеграционные тесты: ПРОПУЩЕНЫ${NC}"
    fi
    
    if [ $DOCKER_SUCCESS -eq 0 ]; then
        echo -e "${GREEN}✓ Docker-тесты: УСПЕШНО${NC}"
    elif [ $DOCKER_SUCCESS -eq 1 ]; then
        echo -e "${RED}✗ Docker-тесты: НЕ ПРОЙДЕНЫ${NC}"
    else
        echo -e "${YELLOW}- Docker-тесты: ПРОПУЩЕНЫ${NC}"
    fi
    
    # Возвращаем общий результат
    if [ $INT_SUCCESS -eq 1 ] || [ $DOCKER_SUCCESS -eq 1 ]; then
        return 1
    else
        return 0
    fi
}

# Запускаем основную функцию с переданными аргументами
main "$@"
exit $?
