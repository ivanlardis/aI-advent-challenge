# Инструкция по деплою

Руководство по развертыванию AI Advent Chat с PostgreSQL через Docker Compose.

## Требования

- Docker 20.10+
- docker-compose v2
- RAM от 2 ГБ
- Доступ к интернету для скачивания образов

## Локальный запуск

### 1. Подготовка

Клонируйте репозиторий и создайте конфигурацию:

```bash
git clone https://github.com/ivanlardis/lardis.git
cd lardis
cp .env.example .env
```

Отредактируйте `.env` и укажите необходимые параметры:

```env
# OpenRouter API
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=tngtech/deepseek-r1t2-chimera:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# PostgreSQL
POSTGRES_USER=lardis
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=lardis_db
POSTGRES_PORT=5432

# Application
APP_PORT=8000
LOG_LEVEL=INFO
SQL_ECHO=false

# Chainlit Auth
CHAINLIT_USERNAME=admin
CHAINLIT_PASSWORD=1234
CHAINLIT_AUTH_SECRET=run_chainlit_create_secret_to_generate
```

### 2. Первый запуск

Запустите приложение и БД:

```bash
docker-compose up -d
```

Проверьте статус контейнеров:

```bash
docker-compose ps
```

Вы должны увидеть два контейнера в статусе `Up`:
- `lardis_postgres` — база данных
- `lardis_app` — приложение

Просмотрите логи для проверки:

```bash
docker-compose logs -f app
```

Приложение будет доступно на `http://localhost:8000`.

## Управление приложением

### Остановка

```bash
docker-compose stop
```

### Запуск после остановки

```bash
docker-compose start
```

### Перезапуск

```bash
docker-compose restart
```

### Полная остановка с удалением контейнеров

```bash
docker-compose down
```

⚠️ **Внимание:** Это удалит контейнеры, но **сохранит данные** в volume `postgres_data`.

### Полная очистка (включая данные)

```bash
docker-compose down -v
```

⚠️ **ОПАСНО:** Это удалит все данные из БД безвозвратно!

## Обновление версии

Когда выходит новая версия:

```bash
# Получить изменения
git pull origin main

# Остановить текущую версию
docker-compose down

# Пересобрать образ
docker-compose build --no-cache app

# Запустить новую версию
docker-compose up -d

# Проверить логи
docker-compose logs -f app
```

## Деплой на сервер

### Подключение к серверу

```bash
ssh root@your_server_ip
```

### Установка Docker (если не установлен)

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# Установка docker-compose
apt-get update
apt-get install -y docker-compose-plugin
```

### Деплой приложения

Создайте директорию проекта:

```bash
mkdir -p /opt/lardis
cd /opt/lardis
```

Создайте `docker-compose.yml`:

```bash
cat > docker-compose.yml <<'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: lardis_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-lardis}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB:-lardis_db}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - lardis_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-lardis}"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    image: ghcr.io/ivanlardis/lardis:latest
    container_name: lardis_app
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
      OPENROUTER_MODEL: ${OPENROUTER_MODEL:-tngtech/deepseek-r1t2-chimera:free}
      OPENROUTER_BASE_URL: ${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}
      DATABASE_URL: postgresql://${POSTGRES_USER:-lardis}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-lardis_db}
      POSTGRES_HOST: postgres
      POSTGRES_USER: ${POSTGRES_USER:-lardis}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB:-lardis_db}
      POSTGRES_PORT: 5432
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
      SQL_ECHO: ${SQL_ECHO:-false}
      CHAINLIT_USERNAME: ${CHAINLIT_USERNAME:-admin}
      CHAINLIT_PASSWORD: ${CHAINLIT_PASSWORD:-1234}
      CHAINLIT_AUTH_SECRET: ${CHAINLIT_AUTH_SECRET}
    ports:
      - "${APP_PORT:-8000}:8000"
    volumes:
      - .chainlit:/app/.chainlit
    networks:
      - lardis_network

volumes:
  postgres_data:
    driver: local

networks:
  lardis_network:
    driver: bridge
EOF
```

Создайте `.env` с вашими секретами:

```bash
cat > .env <<'EOF'
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=tngtech/deepseek-r1t2-chimera:free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

POSTGRES_USER=lardis
POSTGRES_PASSWORD=secure_password_change_me
POSTGRES_DB=lardis_db

APP_PORT=8000
LOG_LEVEL=INFO
SQL_ECHO=false

CHAINLIT_USERNAME=admin
CHAINLIT_PASSWORD=1234
CHAINLIT_AUTH_SECRET=generate_with_chainlit_create_secret
EOF
```

⚠️ **Замените** `your_api_key_here` и `secure_password_change_me` на реальные значения!

Запустите приложение:

```bash
docker-compose up -d
docker-compose logs -f app
```

### Настройка файрвола

Разрешите доступ к порту приложения:

```bash
# Ubuntu/Debian с ufw
ufw allow 8000/tcp
ufw allow 22/tcp  # SSH
ufw enable
```

### Настройка HTTPS (опционально)

Рекомендуется использовать nginx в качестве reverse proxy с Let's Encrypt сертификатом:

```bash
apt-get install -y nginx certbot python3-certbot-nginx

# Создайте конфигурацию nginx
cat > /etc/nginx/sites-available/lardis <<'EOF'
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

ln -s /etc/nginx/sites-available/lardis /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# Получите SSL сертификат
certbot --nginx -d your_domain.com
```

## Бэкап и восстановление

### Создание бэкапа

```bash
# Создать бэкап БД
docker-compose exec postgres pg_dump -U lardis lardis_db | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Скачать бэкап на локальную машину
scp root@your_server_ip:/opt/lardis/backup_*.sql.gz ./
```

### Восстановление из бэкапа

```bash
# Загрузить бэкап на сервер
scp backup_20241213_120000.sql.gz root@your_server_ip:/opt/lardis/

# Восстановить БД
gunzip -c backup_20241213_120000.sql.gz | docker-compose exec -T postgres psql -U lardis lardis_db
```

### Автоматический бэкап (cron)

Добавьте в crontab на сервере:

```bash
crontab -e
```

Добавьте строку для ежедневного бэкапа в 3:00:

```
0 3 * * * cd /opt/lardis && docker-compose exec postgres pg_dump -U lardis lardis_db | gzip > /opt/backups/lardis_$(date +\%Y\%m\%d).sql.gz
```

Создайте директорию для бэкапов:

```bash
mkdir -p /opt/backups
```

## Мониторинг

### Просмотр использования ресурсов

```bash
docker stats lardis_app lardis_postgres
```

### Размер БД

```bash
docker-compose exec postgres psql -U lardis lardis_db -c \
  "SELECT pg_size_pretty(pg_database_size('lardis_db'));"
```

### Количество диалогов и сообщений

```bash
docker-compose exec postgres psql -U lardis lardis_db -c \
  "SELECT
    (SELECT COUNT(*) FROM threads) as threads_count,
    (SELECT COUNT(*) FROM steps) as messages_count,
    (SELECT COUNT(*) FROM users) as users_count;"
```

### Логи приложения

```bash
# Онлайн просмотр
docker-compose logs -f app

# Последние 100 строк
docker-compose logs --tail 100 app

# Сохранить логи в файл
docker-compose logs app > app_logs.txt
```

## Очистка данных

### Удаление старых диалогов

Удалить диалоги, не обновлявшиеся более 30 дней:

```bash
docker-compose exec postgres psql -U lardis lardis_db -c "
DELETE FROM threads
WHERE \"updatedAt\" < (NOW() AT TIME ZONE 'UTC' - INTERVAL '30 days')::TEXT;
"
```

### Очистка всех данных

```bash
docker-compose exec postgres psql -U lardis lardis_db -c "
TRUNCATE TABLE feedbacks, elements, steps, threads, users CASCADE;
"
```

## Troubleshooting

### Приложение не запускается

Проверьте логи:

```bash
docker-compose logs app
```

Частые проблемы:
- Не указан `OPENROUTER_API_KEY` в `.env`
- Неверный формат `DATABASE_URL`
- PostgreSQL еще не готов (подождите 10-15 секунд)

### БД недоступна

Проверьте статус PostgreSQL:

```bash
docker-compose logs postgres
docker-compose exec postgres pg_isready -U lardis
```

### Низкая производительность

Проверьте ресурсы:

```bash
docker stats lardis_app lardis_postgres
```

Убедитесь что:
- Достаточно RAM (минимум 2 ГБ)
- Volume `postgres_data` на локальном диске (не NFS)
- Используется SSD для хранения данных

### История не сохраняется

Проверьте таблицы в БД:

```bash
docker-compose exec postgres psql -U lardis lardis_db
\dt
SELECT COUNT(*) FROM threads;
SELECT COUNT(*) FROM steps;
```

Если таблицы пустые, проверьте логи на ошибки сохранения.

## Безопасность

1. **Не публикуйте порт PostgreSQL (5432)** наружу
2. Используйте **сильные пароли** для `POSTGRES_PASSWORD`
3. Настройте **файрвол** (разрешите только нужные порты)
4. Используйте **HTTPS** через nginx reverse proxy
5. Регулярно делайте **бэкапы**
6. Обновляйте Docker образы для получения патчей безопасности

## Полезные команды

```bash
# Перезагрузить только приложение
docker-compose restart app

# Посмотреть логи PostgreSQL
docker-compose logs -f postgres

# Подключиться к БД
docker exec -it lardis_postgres psql -U lardis lardis_db

# Посмотреть переменные окружения
docker-compose exec app env | grep -E "OPENROUTER|DATABASE|POSTGRES"

# Остановить и удалить всё (кроме данных)
docker-compose down

# Пересобрать образ приложения
docker-compose build --no-cache app

# Обновить образ из registry
docker-compose pull app
docker-compose up -d
```