# {{PROJECT_NAME}}

{{DESCRIPTION}}

## Stack

- **Backend**: Ktor 2.x + Exposed + Kotlinx-html
- **Database**: PostgreSQL 15
- **Proxy**: Nginx latest
- **ORM**: Exposed (SQL DSL)

## Локальный запуск

```bash
docker compose up
```

Приложение будет доступно на http://localhost:80

## Деплой

Деплой происходит автоматически через GitHub Actions при каждом push в любую ветку.

### Настройка VPS

VPS настраивается автоматически Project Starter CLI:
- Docker установлен
- SSH ключи добавлены
- GitHub Secrets настроены

### GitHub Secrets

Следующие секреты автоматически создаются CLI:
- `VPS_HOST` - хост VPS
- `VPS_USER` - пользователь SSH
- `SSH_PRIVATE_KEY` - приватный SSH ключ для подключения

## Структура проекта

```
.
├── src/main/kotlin/       # Ktor приложение
├── src/main/resources/    # Конфигурация
├── Dockerfile             # Сборка app контейнера
├── docker-compose.yml     # App + DB + Nginx
├── build.gradle.kts       # Gradle конфиг
└── .github/workflows/     # CI/CD
```

## Разработка

### Добавление endpoint

В `Application.kt` в блоке `routing` добавьте:

```kotlin
get("/api/hello") {
    call.respondText("Hello World!")
}
```

### Миграции БД

Используйте Exposed миграции в `src/main/kotlin/migrations/`.

## Production

Проект автоматически разворачивается на VPS после каждого push.
