# Установка Photo Agent на Ubuntu 22.04

Это руководство описывает процесс установки и запуска Photo Agent в контейнере Docker на Ubuntu 22.04 с доступом к сервису в локальной сети.

## Требования

- Ubuntu 22.04 LTS
- Права администратора (sudo)
- Подключение к интернету для загрузки пакетов

## Быстрая установка

1. Скачайте или клонируйте репозиторий:

```bash
git clone <url-репозитория> foto-erni
cd foto-erni
```

2. Сделайте скрипт установки исполняемым и запустите его:

```bash
chmod +x setup-ubuntu.sh
sudo ./setup-ubuntu.sh
```

3. Запустите контейнер:

```bash
./run-ubuntu.sh start
```

4. Откройте веб-интерфейс по адресу:
```
http://localhost:8080
```

## Ручная установка

Если вы предпочитаете выполнить установку вручную, следуйте этим шагам:

1. Установите Docker и Docker Compose:

```bash
# Установка Docker
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.18.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER
# Перезагрузите сессию, чтобы изменения вступили в силу
```

2. Создайте необходимые директории:

```bash
mkdir -p data/downloads data/metadata data/analysis data/upload/metadata data/uploaded data/reports data/registry data/processed logs
chmod -R 755 data logs
```

3. Соберите Docker-образ:

```bash
docker-compose -f docker-compose.ubuntu.yml build
```

4. Запустите контейнер:

```bash
docker-compose -f docker-compose.ubuntu.yml up -d
```

## Доступ к локальной сети

В проекте предусмотрены три режима работы с сетью:

### 1. Стандартный режим (по умолчанию)

Использует файл `docker-compose.ubuntu.yml` и стандартную сеть Docker с проброской портов:

```bash
./run-ubuntu.sh start
```

В этом режиме:
- Веб-интерфейс доступен по адресу http://localhost:8080
- Контейнер изолирован от хост-сети, но может обращаться к интернету
- Порты контейнера проброшены на хост-машину (5000 -> 8080)
- Доступ только с локального компьютера

### 2. Режим с доступом к локальной сети

Использует файл `docker-compose.network.yml` и режим сети `host`:

```bash
./run-ubuntu.sh network
```

В этом режиме:
- Контейнер имеет прямой доступ к сетевым интерфейсам хоста
- Контейнер может обращаться к сервисам в локальной сети так же, как и хост-машина
- Контейнер использует IP-адрес хоста для внешних подключений
- Веб-интерфейс доступен по адресу http://localhost:5000 (порт 5000 напрямую)
- Доступ только с локального компьютера

### 3. Режим с доступом из локальной сети

Использует файл `docker-compose.remote.yml` и открывает порт 5001 для всех сетевых интерфейсов:

```bash
./run-ubuntu.sh remote
```

В этом режиме:
- Контейнер доступен из локальной сети по IP-адресу компьютера
- Веб-интерфейс доступен по адресу http://IP-АДРЕС:5001
- Другие компьютеры в локальной сети могут подключаться к сервису

Чтобы узнать IP-адрес вашего компьютера, выполните команду:

```bash
./run-ubuntu.sh ip
```

Выберите режим в зависимости от ваших потребностей.

## Управление контейнером

Для управления контейнером используйте скрипт `run-ubuntu.sh`:

```bash
# Сделайте скрипт исполняемым
chmod +x run-ubuntu.sh

# Запуск контейнера (стандартный режим)
./run-ubuntu.sh start

# Запуск с доступом к локальной сети
./run-ubuntu.sh network

# Запуск с доступом из локальной сети
./run-ubuntu.sh remote

# Показать IP-адрес компьютера
./run-ubuntu.sh ip

# Остановка контейнера
./run-ubuntu.sh stop

# Перезапуск контейнера (стандартный режим)
./run-ubuntu.sh restart

# Перезапуск с доступом из локальной сети
./run-ubuntu.sh restart-remote

# Просмотр логов
./run-ubuntu.sh logs

# Открытие оболочки в контейнере
./run-ubuntu.sh shell

# Запуск веб-интерфейса в интерактивном режиме
./run-ubuntu.sh web

# Запуск веб-интерфейса с доступом из локальной сети
./run-ubuntu.sh web-remote

# Запуск полного процесса обработки
./run-ubuntu.sh process

# Получение схемы метаданных
./run-ubuntu.sh schema

# Обработка фотографий
./run-ubuntu.sh photos

# Анализ с помощью OpenAI
./run-ubuntu.sh analyze

# Генерация метаданных
./run-ubuntu.sh metadata

# Загрузка в SharePoint
./run-ubuntu.sh upload

# Пересборка Docker-образа
./run-ubuntu.sh build

# Показать справку
./run-ubuntu.sh help
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
./run-ubuntu.sh restart
```

## Устранение неполадок

### Проблемы с Docker

Если у вас возникли проблемы с Docker:

```bash
# Остановить все контейнеры
docker-compose -f docker-compose.ubuntu.yml down

# Удалить все образы и контейнеры
docker system prune -a

# Повторить установку
sudo ./setup-ubuntu.sh
```

### Проблемы с доступом к файлам

Если возникают проблемы с правами доступа к файлам:

```bash
# Установить правильные разрешения
sudo chmod -R 755 data logs
sudo chown -R $USER:$USER data logs
```

### Проблемы с сетью

Если возникают проблемы с доступом к локальной сети:

```bash
# Проверить IP-адрес компьютера
./run-ubuntu.sh ip

# Проверить настройки сети Docker
docker network ls
docker network inspect bridge

# Проверить режим сети контейнера
docker inspect photo-agent-remote | grep NetworkMode

# Проверить открытые порты
sudo netstat -tulpn | grep 5001

# Проверить настройки брандмауэра
sudo ufw status
```

Если брандмауэр активен, возможно, нужно открыть порт 5001:

```bash
sudo ufw allow 5001/tcp
```

## Дополнительная информация

Для получения дополнительной информации о проекте обратитесь к основной документации в файле `README.md`.
