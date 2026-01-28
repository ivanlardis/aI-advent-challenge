# God Agent - Спецификация

## Обзор
God Agent — личный AI-помощник, объединяющий все Chainlit-реализации из AI Advent Challenge в одно приложение.

## Источники функционала
- **Challenge 1:** OpenRouter чат (LangChain интеграция)
- **Challenge 9:** Суммаризация истории + статистика токенов
- **Challenge 12:** MCP клиент (context7)
- **Challenge 19:** RAG с источниками
- **Challenge 27:** Streaming ответов
- **Challenge 29:** Аналитик файлов (CSV/JSON/LOG)
- **Challenge 30:** Персонализация из profile.md

## Технические решения

### LLM
- **Провайдер:** OpenRouter
- **Модель по умолчанию:** `anthropic/claude-3.5-sonnet`
- **Переменные окружения:**
  - `OPENROUTER_API_KEY` (обязательно)
  - `OPENROUTER_MODEL` (опционально)
  - `OPENROUTER_BASE_URL` (опционально, default: https://openrouter.ai/api/v1)

### RAG
- **Хранилище:** FAISS
- **Embeddings:** `paraphrase-multilingual-MiniLM-L12-v2`
- **Данные:** `data/rag_example_cities_ru.txt` (города России)
- **Индекс:** `data/faiss_index/`

### MCP
- **Endpoint:** context7 MCP
- **Переменные:**
  - `CONTEXT7_MCP_ENDPOINT` (default: https://mcp.context7.com/mcp)
  - `CONTEXT7_API_KEY`

### Персонализация
- **Файл профиля:** `config/profile.md`
- **Формат:** Markdown с структурой из Challenge 30

### История
- **Хранение:** только в сессии Chainlit (без БД)
- **Сжатие:** команда `/compress`

## Слэш-команды

| Команда | Описание |
|---------|----------|
| `/compress` | Сжать историю диалога в краткую сводку |
| `/summary` | Показать статистику использования токенов |
| `/rag on\|off` | Включить/выключить RAG поиск |
| `/mcp` | Показать доступные инструменты context7 |

## Загрузка файлов
- **Способ:** drag & drop через Chainlit UI
- **Форматы:** CSV, JSON, LOG, TXT
- **Лимит:** 10MB
- **Обработка:** chunked для больших файлов

## UI

### Название
God Agent

### Приветствие
Персонализированное с учётом profile.md (имя пользователя)

### Вывод
- Простой текст для аналитика файлов
- Markdown для RAG источников
- Streaming для ответов LLM

## Структура файлов

```
/
├── app.py                          # Главный файл приложения
├── requirements.txt                # Зависимости
├── chainlit.md                     # Описание для Chainlit UI
├── .env.example                    # Пример переменных окружения
├── config/
│   ├── profile.md                  # Профиль пользователя
│   └── profile.example.md          # Шаблон профиля
├── data/
│   ├── rag_example_cities_ru.txt   # Данные для RAG
│   └── faiss_index/                # FAISS индекс
└── lib/
    ├── openrouter_client.py        # Клиент OpenRouter
    ├── mcp_client.py               # Клиент MCP
    └── rag_service.py              # RAG сервис
```

## Запуск

```bash
# Установка зависимостей
pip install -r requirements.txt

# Настройка окружения
export OPENROUTER_API_KEY=sk-or-v1-...
export CONTEXT7_API_KEY=ctx7sk-...

# Запуск
chainlit run app.py
```

## Зависимости

```
chainlit>=2.3.0
langchain>=0.3.0
langchain-openai>=0.2.0
requests>=2.31.0
faiss-cpu>=1.7.0
sentence-transformers>=2.2.0
python-dotenv>=1.0.0
```

## Конфигурация

### .env.example
```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
CONTEXT7_API_KEY=ctx7sk-your-key-here
```

## Решения по компромиссам

1. **RAG всегда включен по умолчанию** — можно выключить командой `/rag off`
2. **Без постоянной БД** — история только в сессии, проще деплой
3. **Monolith архитектура** — всё в одном app.py для простоты
4. **OpenRouter вместо локальной LLM** — надёжнее и быстрее

## Автор
Создано на основе AI Advent Challenge (декабрь 2025 — январь 2026)
