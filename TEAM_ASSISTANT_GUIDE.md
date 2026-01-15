# Team Assistant - Руководство пользователя

AI-ассистент для приоритизации задач на основе анализа коммитов, свежести и документации.

## 🚀 Быстрый старт

### 1. Сборка

```bash
./gradlew clean build shadowJar
```

### 2. Создание GitHub Token

1. Перейдите на https://github.com/settings/tokens
2. Нажмите "Generate new token" → "Generate new token (classic)"
3. Выберите права:
   - ✅ `repo` (для доступа к issues и commits)
   - ✅ `read:org` (если используете приватные репо организации)
4. Скопируйте токен

### 3. Настройка конфигурации

При первом запуске автоматически создается `.team-assistant/config.json`.

Отредактируйте его:

```json
{
  "github": {
    "owner": "ваш-логин",
    "repo": "ваш-репозиторий",
    "maxIssues": 30,
    "maxCommits": 50
  }
}
```

### 4. Запуск

**Через переменную окружения:**

```bash
export GITHUB_TOKEN="ghp_ваш_токен"
java -jar backend/build/libs/project-assistant-1.0.0.jar team-assistant
```

**Или введите токен при запуске:**

```bash
java -jar backend/build/libs/project-assistant-1.0.0.jar team-assistant
# Введите токен когда спросят
```

Сервер запустится на `http://localhost:8080`

## 📡 API Endpoints

### Health Check

```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "status": "ok",
  "service": "team-assistant"
}
```

### Получение задач с приоритетами

```bash
curl http://localhost:8080/api/issues
```

Response (массив задач отсортирован по приоритету):

```json
[
  {
    "issue": {
      "number": 123,
      "title": "Fix authentication bug",
      "state": "open",
      "created_at": "2026-01-10T10:00:00Z",
      "updated_at": "2026-01-15T14:30:00Z"
    },
    "priorityScore": 0.87,
    "commitCount": 42,
    "commitScore": 0.84,
    "recencyScore": 0.95,
    "ragScore": 0.12
  }
]
```

### Детали задачи

```bash
curl http://localhost:8080/api/issues/123
```

### Обновление конфигурации

```bash
curl -X POST http://localhost:8080/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "github": {
      "owner": "my-login",
      "repo": "my-repo",
      "maxIssues": 50,
      "maxCommits": 100
    },
    "scoring": {
      "weights": {
        "commitActivity": 0.7,
        "recency": 0.2,
        "ragRelevance": 0.1
      }
    }
  }'
```

### Обновление кэша

```bash
curl -X POST http://localhost:8080/api/issues/cache/refresh
```

### Статистика кэша

```bash
curl http://localhost:8080/api/cache/stats
```

## ⚙️ Конфигурация

### Полный пример `.team-assistant/config.json`

```json
{
  "github": {
    "owner": "lardisz",
    "repo": "project-assistant",
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

### Параметры

#### GitHub

- `owner` - владелец репозитория (обязательно)
- `repo` - название репозитория (обязательно)
- `maxIssues` - максимальное количество задач для анализа (по умолчанию 30)
- `maxCommits` - максимальное количество коммитов для нормализации (по умолчанию 50)

#### Scoring (веса должны суммироваться в 1.0)

- `commitActivity` (0.6) - вес активности коммитов
- `recency` (0.3) - вес свежести задачи
- `ragRelevance` (0.1) - вес релевантности документации

#### Cache

- `enabled` (true) - включить кэширование
- `ttlMinutes` (60) - время жизни кэша в минутах
- `filePath` - путь к файлу кэша

#### Server

- `port` (8080) - порт сервера
- `host` ("0.0.0.0") - хост для привязки

## 🧮 Расчет приоритета

```
priority = 0.6 * commit_activity + 0.3 * recency + 0.1 * rag_relevance
```

### Commit Activity (0.6)

Количество коммитов связанных с задачей, нормализовано к 0-1:
- 0 коммитов → 0.0
- 50+ коммитов → 1.0

### Recency (0.3)

Exponential decay на основе времени последнего обновления:
- 0 дней → 1.0
- 30 дней → ~0.37
- 60 дней → ~0.14

### RAG Relevance (0.1)

Максимальная схожесть с документацией проекта через RAG поиск:
- Нет релевантных документов → 0.0
- Высокая релевантность → 1.0

## 🔒 Безопасность

### GitHub Token

- Никогда не коммитьте токен в репозиторий!
- Используйте переменную окружения `GITHUB_TOKEN`
- Токен сохраняется только в памяти процесса
- Рекомендуется создавать токен с минимальными правами (`repo` только)

### Рекомендации

1. Используйте `.gitignore` для `.team-assistant/` (токен не сохраняется)
2. Создавайте отдельный токен для каждого проекта
3. Периодически обновляйте токены
4. Используйте `read-only` токены где возможно

## 🐛 Troubleshooting

### "GitHub token is required!"

**Решение:** Установите переменную окружения или введите токен при запуске:

```bash
export GITHUB_TOKEN="ghp_..."
java -jar backend/build/libs/project-assistant-1.0.0.jar team-assistant
```

### "Please set github.owner and github.repo"

**Решение:** Отредактируйте `.team-assistant/config.json`:

```json
{
  "github": {
    "owner": "ваш-логин",
    "repo": "ваш-репо"
  }
}
```

### "Failed to fetch issues"

**Причины:**
1. Неверный токен
2. Репозиторий не существует или нет доступа
3. Превышен rate limit (5000 requests/hour)

**Решение:**
- Проверьте токен: https://github.com/settings/tokens
- Проверьте доступ к репозиторию
- Проверьте rate limit: `curl -H "Authorization: Bearer $TOKEN" https://api.github.com/rate_limit`

### Порт уже занят

**Решение:** Измените порт в `config.json`:

```json
{
  "server": {
    "port": 8081
  }
}
```

## 📊 Примеры использования

### PowerShell

```powershell
# Установка токена
$env:GITHUB_TOKEN = "ghp_..."

# Запуск
java -jar backend\build\libs\project-assistant-1.0.0.jar team-assistant

# Получение задач
Invoke-RestMethod -Uri http://localhost:8080/api/issues
```

### Python

```python
import requests

# Получение задач
response = requests.get('http://localhost:8080/api/issues')
issues = response.json()

# Вывод top-5
for issue in issues[:5]:
    print(f"#{issue['issue']['number']}: {issue['issue']['title']}")
    print(f"  Priority: {issue['priorityScore']:.2f}")
    print(f"  Commits: {issue['commitCount']}")
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

// Получение задач
axios.get('http://localhost:8080/api/issues')
  .then(response => {
    const issues = response.data;
    console.log(`Top issue: #${issues[0].issue.number} - ${issues[0].issue.title}`);
    console.log(`Priority: ${issues[0].priorityScore.toFixed(2)}`);
  });
```

## 📝 Логи

Логи сервера выводятся в stdout:

```
🚀 Starting Team Assistant...
📁 Project directory: .
⚙️  Config loaded: lardisz/project-assistant
📊 Max issues: 30, Max commits: 50
INFO  Starting Team Assistant server on 0.0.0.0:8080
INFO  Config: maxIssues=30, maxCommits=50
INFO  Scoring weights: commit=0.6, recency=0.3, rag=0.1
INFO  GitHub client initialized
```

## 🎯 Следующие шаги

- Создайте frontend (Kotlin/JS + Compose, React, etc.)
- Настройте CI/CD интеграцию
- Добавьте WebSocket для real-time updates
- Настройте мониторинг и метрики

## 📚 Дополнительные ресурсы

- [GitHub REST API](https://docs.github.com/en/rest)
- [Ktor Documentation](https://ktor.io/docs/)
- [Kotlin Serialization](https://github.com/Kotlin/kotlinx.serialization)

## 📄 Лицензия

MIT
