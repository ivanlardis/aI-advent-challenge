# Team Assistant

AI-ассистент для приоритизации задач на основе анализа истории коммитов, свежести и документации проекта.

## Возможности

- **Автоматический расчёт приоритета** задач на основе:
  - Активности коммитов (60%)
  - Свежести задачи (30%)
  - Релевантности документации RAG (10%)

- **GitHub API интеграция** для:
  - Получения списка issues
  - Timeline API для связей с коммитами
  - Rate limiting handling

- **Кэширование** результатов в JSON для быстрой загрузки

- **REST API** для интеграции с фронтендом

## Установка

### Требования

- JDK 17+
- Gradle 8.x

### Сборка

```bash
./gradlew clean build shadowJar
```

## Использование

### Запуск сервера

```bash
java -jar backend/build/libs/project-assistant-1.0.0.jar team-assistant
```

Сервер запустится на `http://localhost:8080`

### Конфигурация

При первом запуске создается файл `.team-assistant/config.json`:

```json
{
  "github": {
    "owner": "",
    "repo": "",
    "maxIssues": 30,
    "maxCommits": 50
  },
  "scoring": {
    "weights": {
      "commitActivity": 0.6,
      "recency": 0.3,
      "ragRelevance": 0.1
    }
  },
  "cache": {
    "enabled": true,
    "ttlMinutes": 60,
    "filePath": ".team-assistant/cache.json"
  },
  "server": {
    "port": 8080,
    "host": "0.0.0.0"
  }
}
```

Отредактируйте поле `github.owner` и `github.repo` для вашего репозитория.

## API Endpoints

### Health Check

```
GET /health
```

Response:
```json
{
  "status": "ok",
  "service": "team-assistant"
}
```

### Конфигурация

```
GET /api/config
POST /api/config
```

### Задачи

```
GET /api/issues
```

Возвращает список задач с приоритетами (отсортирован по убыванию).

### Детали задачи

```
GET /api/issues/{number}
```

Возвращает детальную информацию о задаче с timeline.

### Кэш

```
GET /api/cache/stats
POST /api/cache/refresh
```

## Архитектура

```
┌──────────────────────────────────────────────────────────────────┐
│                      Ktor Server (Backend)                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    API Layer                              │   │
│  │  IssuesApi | AuthApi | ConfigApi                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│           │                    │                                 │
│           ▼                    ▼                                 │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │  GitHubClient    │  │  PriorityCalculator                      │
│  │  (Ktor HTTP)     │  │  (Commit+Recency+RAG)                   │
│  └──────────────────┘  └──────────────────┘                     │
│           │                    │                                 │
│           ▼                    ▼                                 │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │  IssueCache      │  │  RagService      │                     │
│  │  (JSON file)     │  │  (Существующий)  │                     │
│  └──────────────────┘  └──────────────────┘                     │
└──────────────────────────────────────────────────────────────────┘
```

## Структура проекта

```
backend/src/main/kotlin/
├── teamassistant/
│   ├── server/          # Ktor server setup
│   ├── api/             # API endpoints
│   ├── github/          # GitHub client & service
│   ├── cache/           # JSON cache layer
│   ├── scoring/         # Priority calculator
│   └── config/          # Config loader
├── rag/                 # Существующий RAG модуль
└── cli/                 # TeamAssistantCommand
```

## Приоритизация

### Формула

```
priority = 0.6 * commit_activity + 0.3 * recency + 0.1 * rag_relevance
```

### Commit Activity (0.6)

- Подсчёт коммитов связанных с issue
- Нормализация: 0 commits → 0.0, 50+ commits → 1.0

### Recency (0.3)

- Exponential decay: `e^(-days_since_update / 30)`
- 0 дней → 1.0, 30 дней → ~0.37, 60 дней → ~0.14

### RAG Relevance (0.1)

- Поиск релевантных документов через существующий RagService
- Максимальная схожесть среди top-K результатов

## Development

### Запуск в dev режиме

```bash
./gradlew :backend:run --args="team-assistant"
```

### Тестирование

```bash
./gradlew test
```

## Следующие шаги

- [ ] Frontend на Kotlin/JS + Compose Web
- [ ] Docker конфигурация для разработки
- [ ] GitHub OAuth flow
- [ ] WebSocket для real-time updates
- [ ] Метрики и мониторинг

## Лицензия

MIT
