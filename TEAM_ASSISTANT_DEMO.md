# Team Assistant - Синтетические данные

## 📊 Созданный бэклог

В `.team-assistant/cache.json` созданы 12 синтетических issues для демонстрации работы системы.

### Top приоритетные задачи:

1. **#1 - Fix authentication bug in login flow** (Priority: 0.87)
   - 42 коммита, высокая активность
   - RAG relevance: 0.65

2. **#2 - Add dark mode support to dashboard** (Priority: 0.72)
   - 28 коммитов
   - Недавно обновлено

3. **#3 - Implement real-time updates with WebSocket** (Priority: 0.65)
   - 15 коммитов
   - Высокая RAG relevance: 0.82

### Все задачи:

| # | Title | Priority | Commits | RAG |
|---|-------|----------|---------|-----|
| 1 | Fix authentication bug | **0.87** | 42 | 0.65 |
| 2 | Add dark mode support | **0.72** | 28 | 0.45 |
| 3 | WebSocket real-time updates | **0.65** | 15 | 0.82 |
| 4 | Optimize RAG performance | **0.58** | 8 | 0.91 |
| 5 | Add filtering to API | **0.52** | 5 | 0.38 |
| 6 | Docker configuration | **0.48** | 3 | 0.25 |
| 7 | Unit tests for calculator | **0.41** | 2 | 0.15 |
| 8 | Cache invalidation on config | **0.38** | 1 | 0.55 |
| 9 | OpenAPI documentation | **0.32** | 0 | 0.42 |
| 10 | User guide | **0.28** | 0 | 0.18 |
| 11 | Per-repo configuration | **0.24** | 0 | 0.12 |
| 12 | Prometheus metrics | **0.19** | 0 | 0.08 |

## 🚀 Быстрый старт с синтетическими данными

### 1. Синтетические данные уже созданы!

```bash
# Проверить кэш
cat .team-assistant/cache.json | jq '.issues | length'
# Вывод: 12

# Проверить конфиг
cat .team-assistant/config.json | jq '.github'
# Вывод: {"owner":"ivanlardis","repo":"aI-advent-challenge",...}
```

### 2. Запустить сервер (без GitHub токена!)

```bash
java -jar backend/build/libs/project-assistant-1.0.0.jar team-assistant
```

Сервер автоматически использует кэшированные данные.

### 3. Использовать API

```bash
# Получить top-3 задачи
curl -s http://localhost:8080/api/issues | jq '.[:3] | .[] | {
  title: .issue.title,
  priority: .priorityScore,
  commits: .commitCount
}'

# Вывод:
# {
#   "title": "Fix authentication bug in login flow",
#   "priority": 0.87,
#   "commits": 42
# }
# {
#   "title": "Add dark mode support to dashboard",
#   "priority": 0.72,
#   "commits": 28
# }
# {
#   "title": "Implement real-time updates with WebSocket",
#   "priority": 0.65,
#   "commits": 15
# }
```

### 4. Фильтрация по приоритету

```bash
# Только высокоприоритетные задачи (>0.7)
curl -s http://localhost:8080/api/issues | jq '.[] |
  select(.priorityScore > 0.7) | {title, priority}'
```

### 5. Статистика кэша

```bash
curl -s http://localhost:8080/api/cache/stats
# {"exists":true,"size":3482,"lastUpdated":"2026-01-15T15:00:00Z","issuesCount":12}
```

## 🔄 Обновление данных

### Вариант 1: Использовать GitHub API (с токеном)

```bash
export GITHUB_TOKEN="ghp_..."
java -jar backend/build/libs/project-assistant-1.0.0.jar team-assistant

# Обновить кэш реальными данными
curl -X POST http://localhost:8080/api/issues/cache/refresh
```

### Вариант 2: Создать свои синтетические данные

Отредактируйте `.team-assistant/cache.json`:

```json
{
  "issues": [
    {
      "number": 1,
      "title": "Ваша задача",
      "state": "open",
      "created_at": "2026-01-15T10:00:00Z",
      "updated_at": "2026-01-15T15:00:00Z",
      "priority_score": 0.85,
      "commit_count": 30,
      "rag_relevance": 0.70
    }
  ],
  "last_updated": "2026-01-15T15:00:00Z"
}
```

## 📈 Анализ синтетических данных

### Распределение приоритетов

- **High (>0.7)**: 2 задачи (17%)
- **Medium (0.4-0.7)**: 6 задач (50%)
- **Low (<0.4)**: 4 задачи (33%)

### Факторы приоритета

1. **Commit Activity** - основные драйверы:
   - Top-3 все имеют >15 коммитов
   - Задачи без коммитов имеют низкий приоритет

2. **Recency** - свежесть:
   - 6 из 12 обновлены за последние 2 дня
   - Старые задачи (>5 дней) имеют пониженный приоритет

3. **RAG Relevance** - документация:
   - Задача #4 имеет 0.91 (оптимизация RAG)
   - Технические задачи имеют низкую релевантность

## 🎯 Примеры использования

### PowerShell

```powershell
# Получить задачи
$response = Invoke-RestMethod -Uri http://localhost:8080/api/issues

# Top-5 по приоритету
$response | Select-Object -First 5 | ForEach-Object {
    [PSCustomObject]@{
        Issue = "#$($_.issue.number)"
        Title = $_.issue.title
        Priority = "{0:P0}" -f $_.priorityScore
        Commits = $_.commitCount
    }
} | Format-Table -AutoSize
```

### Python

```python
import requests

# Получить задачи
response = requests.get('http://localhost:8080/api/issues')
issues = response.json()

# Анализ
high_priority = [i for i in issues if i['priorityScore'] > 0.7]
print(f"High priority tasks: {len(high_priority)}")

# Top-3
for i in issues[:3]:
    print(f"#{i['issue']['number']}: {i['issue']['title']}")
    print(f"  Priority: {i['priorityScore']:.2f}")
    print(f"  Commits: {i['commitCount']}")
```

### JavaScript

```javascript
// Fetch через браузер
fetch('http://localhost:8080/api/issues')
  .then(r => r.json())
  .then(issues => {
    console.log('Top 3 priority tasks:');
    issues.slice(0, 3).forEach(i => {
      console.log(`#${i.issue.number}: ${i.issue.title}`);
      console.log(`  Score: ${(i.priorityScore * 100).toFixed(0)}%`);
    });
  });
```

## 📝 Доступные endpoints

```bash
GET /health                              # Проверка статуса
GET /api/config                          # Конфигурация
GET /api/issues                          # Все задачи (отсортированы)
GET /api/issues/{id}                     # Детали задачи
POST /api/issues/cache/refresh           # Обновить кэш
GET /api/cache/stats                     # Статистика кэша
```

## 🎨 Визуализация данных

### График приоритетов (через Python)

```python
import requests
import matplotlib.pyplot as plt

response = requests.get('http://localhost:8080/api/issues')
issues = response.json()

# Извлечь данные
numbers = [f"#{i['issue']['number']}" for i in issues]
priorities = [i['priorityScore'] for i in issues]
commits = [i['commitCount'] for i in issues]

# График
plt.figure(figsize=(12, 6))
plt.bar(numbers, priorities, alpha=0.7, label='Priority')
plt.axhline(y=0.7, color='r', linestyle='--', label='High threshold')
plt.xlabel('Issue Number')
plt.ylabel('Priority Score')
plt.title('Team Assistant - Issue Priorities')
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('priorities.png')
print("График сохранен в priorities.png")
```

## 🔧 Troubleshooting

### "Кэш не найден"

**Решение:** Создайте кэш вручную или используйте GitHub API:

```bash
# Создать пустой кэш
cat > .team-assistant/cache.json << EOF
{
  "issues": [],
  "last_updated": "2026-01-15T15:00:00Z"
}
EOF
```

### "Старый кэш"

**Решение:** Обновите `last_updated` на текущую дату:

```bash
# Mac/Linux
date -u +"%Y-%m-%dT%H:%M:%SZ" | xargs -I {} jq --arg last_updated {} '.last_updated = $last_updated' .team-assistant/cache.json > tmp.json && mv tmp.json .team-assistant/cache.json
```

### "Неверный формат JSON"

**Решение:** Валидация через jq:

```bash
jq '.' .team-assistant/cache.json > /dev/null
echo $?  # 0 = OK, 3 = Error
```

## 📚 Дополнительные ресурсы

- [TEAM_ASSISTANT_GUIDE.md](./TEAM_ASSISTANT_GUIDE.md) - полное руководство
- [TEAM_ASSISTANT_README.md](./TEAM_ASSISTANT_README.md) - техническая документация

---

**Создано:** 2026-01-15
**Issues:** 12 синтетических задач
**Цель:** Демонстрация работы Team Assistant
