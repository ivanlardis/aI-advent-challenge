## LLM-прокси через OpenRouter (Chainlit + LangChain)

Простой чат-интерфейс на Chainlit, который проксирует запросы в OpenRouter через LangChain.

### Структура
- `app/chainlit_app.py` — веб-интерфейс Chainlit (хуки чата).
- `app/langchain_client.py` — сборка LangChain-цепочки, обращающейся к OpenRouter.
- `Dockerfile` — контейнер для запуска Chainlit.

### Переменные окружения
- `OPENROUTER_API_KEY` (обязательно) — токен с https://openrouter.ai.
- `OPENROUTER_MODEL` (опционально) — ID модели, по умолчанию `x-ai/grok-4.1-fast:free` (бесплатно до 3 декабря 2025).
- `OPENROUTER_BASE_URL` (опционально) — базовый URL, по умолчанию `https://openrouter.ai/api/v1`.

### Локальный запуск
```bash
pip install -r requirements.txt
OPENROUTER_API_KEY=... chainlit run app/chainlit_app.py --host 0.0.0.0 --port 8000 --headless
```
Открыть http://localhost:8000 и начать диалог.

### Docker
```bash
docker build -t lardis .
docker run -d -p 38542:8000 \
  -e OPENROUTER_API_KEY=... \
  lardis
```

### Что внутри
- Chainlit UI, который хранит цепочку в сессии и отвечает на сообщения.
- LangChain цепочка (prompt → ChatOpenAI → StrOutputParser) с конфигурацией через окружение.
- Контейнерная сборка готова к публикации в GHCR и запуску на VPS.

### Как работает код
- `build_chain()` в `app/langchain_client.py` читает переменные окружения, создает `ChatOpenAI` с базовым URL OpenRouter, добавляет системный промт на русском и парсер ответа.
- Chainlit-хуки в `app/chainlit_app.py`:
  - `on_chat_start` — инициализирует цепочку, кладет ее в сессию и отправляет приветствие.
  - `on_message` — берет цепочку из сессии, отправляет пользовательский ввод и возвращает ответ.
- Любые ошибки инициализации (например, нет `OPENROUTER_API_KEY`) сразу показываются в интерфейсе.
