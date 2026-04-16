# CLAUDE.md — God Agent (lardis)

## Что это
Персональный AI-помощник. Chainlit чат-бот + OpenRouter LLM + профиль пользователя.

## Стек
Python 3.13 · Chainlit · LangChain (`ChatOpenAI`) · OpenRouter API

## Структура
```
app.py                        # Точка входа: хендлеры, команды, system prompt
lib/openrouter_client.py      # OpenRouter клиент (LangChain обёртка)
config/profile.md             # Профиль пользователя (gitignored)
config/profile.example.md     # Шаблон профиля
```

## Правила

### Можно
- Добавлять новые модули в `lib/`
- Добавлять новые команды (`/command`) в `app.py`
- Расширять system prompt
- Использовать `cl.user_session` для хранения состояния сессии

### Нельзя
- Создавать новые папки верхнего уровня (только `lib/`, `config/`, `data/`)
- Менять структуру `OpenRouterClient` (контракт используется везде)
- Хранить секреты в коде — только `.env`
- Использовать глобальное mutable-состояние (всё через `cl.user_session`)
- Выдумывать API — если не уверен что метод/декоратор существует, не используй

### Стиль кода
- Docstrings и комментарии на русском
- Async для всех хендлеров и клиентских методов
- Типизация через `typing` (List, Dict, Optional)
- Без эмодзи в коде и строках

### Паттерн добавления команды
```python
# В on_message, блок обработки команд:
if cmd == "/mycommand":
    await handle_mycommand(...)
    return
```

### Антипаттерны
- `analytics = Analytics()` на уровне модуля — НЕТ, состояние через `cl.user_session`
- `@cl.page()` — НЕ существует в Chainlit, не выдумывай декораторы
- `len(text.split())` как подсчёт токенов — это слова, не токены
- Прямой `import requests` — используй `OpenRouterClient`

## Запуск
```bash
source venv/bin/activate && chainlit run app.py
```

## Env
- `OPENROUTER_API_KEY` (обязательно)
- `OPENROUTER_MODEL` (default: `anthropic/claude-3.5-sonnet`)
- `OPENROUTER_BASE_URL` (default: `https://openrouter.ai/api/v1`)
