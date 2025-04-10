#!/bin/bash
# Скрипт для запуска интеграционных тестов

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

# Функция для запуска unit-тестов
run_unit_tests() {
    echo -e "\n${GREEN}Запуск модульных тестов...${NC}"
    python -m unittest discover -s tests -p "test_integration.py"
    local TEST_RESULT=$?
    if [ $TEST_RESULT -ne 0 ]; then
        echo -e "${RED}Модульные тесты не пройдены!${NC}"
        return 1
    else
        echo -e "${GREEN}Модульные тесты успешно пройдены!${NC}"
        return 0
    fi
}

# Функция для запуска интеграционных тестов Docker
run_docker_tests() {
    echo -e "\n${GREEN}Запуск тестов Docker-контейнера...${NC}"
    
    # Проверяем, установлен ли Docker
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Ошибка: Docker Compose не установлен${NC}"
        return 1
    fi
    
    # Запускаем тесты Docker
    python -m unittest tests/test_docker.py
    local TEST_RESULT=$?
    if [ $TEST_RESULT -ne 0 ]; then
        echo -e "${RED}Тесты Docker-контейнера не пройдены!${NC}"
        return 1
    else
        echo -e "${GREEN}Тесты Docker-контейнера успешно пройдены!${NC}"
        return 0
    fi
}

# Основная функция
main() {
    local UNIT_SUCCESS=0
    local DOCKER_SUCCESS=0
    
    # Проверяем аргументы
    if [ "$1" == "unit" ]; then
        run_unit_tests
        UNIT_SUCCESS=$?
        DOCKER_SUCCESS=1  # Пропускаем Docker-тесты
    elif [ "$1" == "docker" ]; then
        run_docker_tests
        DOCKER_SUCCESS=$?
        UNIT_SUCCESS=1  # Пропускаем модульные тесты
    else
        # Запускаем все тесты
        run_unit_tests
        UNIT_SUCCESS=$?
        
        run_docker_tests
        DOCKER_SUCCESS=$?
    fi
    
    # Выводим итоговый результат
    echo -e "\n${GREEN}=== Результаты тестирования ===${NC}"
    if [ $UNIT_SUCCESS -eq 0 ]; then
        echo -e "${GREEN}✓ Модульные тесты: УСПЕШНО${NC}"
    elif [ $UNIT_SUCCESS -eq 1 ]; then
        echo -e "${RED}✗ Модульные тесты: НЕ ПРОЙДЕНЫ${NC}"
    else
        echo -e "${YELLOW}- Модульные тесты: ПРОПУЩЕНЫ${NC}"
    fi
    
    if [ $DOCKER_SUCCESS -eq 0 ]; then
        echo -e "${GREEN}✓ Тесты Docker: УСПЕШНО${NC}"
    elif [ $DOCKER_SUCCESS -eq 1 ]; then
        echo -e "${RED}✗ Тесты Docker: НЕ ПРОЙДЕНЫ${NC}"
    else
        echo -e "${YELLOW}- Тесты Docker: ПРОПУЩЕНЫ${NC}"
    fi
    
    # Возвращаем общий результат
    if [ $UNIT_SUCCESS -ne 0 ] || [ $DOCKER_SUCCESS -ne 0 ]; then
        return 1
    else
        return 0
    fi
}

# Запускаем основную функцию с переданными аргументами
main "$@"
exit $?
