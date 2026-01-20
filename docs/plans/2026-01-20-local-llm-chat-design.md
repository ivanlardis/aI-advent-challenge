# Дизайн: Chainlit приложение с локальной LLM (Ollama)

## Задача
Интегрировать локальную LLM в Chainlit приложение с сессионной историей диалога, выбором модели и метриками генерации.

## Архитектура

**Структура приложения:**
- `app/chainlit_app.py` - главный файл Chainlit с обработкой событий чата
- `app/ollama_client.py` - клиент для работы с Ollama API
- `app/history.py` - менеджер сессионной истории сообщений
- `requirements.txt` - зависимости Python
- `.env.example` - пример конфигурации

**Компоненты:**

1. **OllamaClient** - HTTP клиент для Ollama API
   - Методы: `list_models()`, `generate_stream(messages, model)`
   - Обработка ошибок connection
   - Подсчёт токенов и времени

2. **SessionHistory** - хранение истории в памяти
   - Список сообщений с ролями (user/assistant)
   - Методы: `add_message()`, `get_for_api()`, `clear()`

3. **Chainlit handlers**
   - `on_chat_start` - инициализация, выбор модели, приветствие
   - `on_message` - обработка сообщений с историей
   - `on_chat_end` - очистка сессии

## Поток данных

**Инициализация чата:**
1. Пользователь открывает приложение → `on_chat_start`
2. OllamaClient запрашивает `/api/tags` для списка моделей
3. Если моделей нет → показываем ошибку с инструкцией
4. Если есть → отправляем dropdown для выбора модели
5. Сохраняем модель и создаем `SessionHistory` в `user_session`

**Обработка сообщения:**
1. Пользователь отправляет сообщение → `on_message`
2. Извлекаем историю и модель из сессии
3. Добавляем сообщение в `SessionHistory`
4. POST на `http://localhost:11434/api/chat` с `stream: true`
5. Замеряем время начала
6. Stream ответ (NDJSON), парсим каждую строку
7. Для каждого chunk обновляем сообщение через `.stream_token()`
8. Считаем метрики из финального ответа
9. Добавляем ответ в историю
10. Добавляем метрики: `⏱ X сек • 🔢 Y символов`

## Обработка ошибок

**Ошибки подключения:**
- Connection refused → "❌ Ollama не запущен. Запустите: `ollama serve`"
- Пустой список моделей → "📦 Моделей нет. Установите: `ollama pull gemma2:2b`"
- Ошибка генерации → "⚠️ Ошибка: {message}", история сохраняется

**UX улучшения:**
- Dropdown с моделями при старте: "gemma2:2b (4.3GB)"
- Typing indicator во время генерации
- Stream вывод для реального времени
- Метрики под каждым ответом: `⏱ 2.3 сек • 🔢 127 символов • 📊 56 ток/сек`

## Реализация компонентов

**app/ollama_client.py:**
```python
import requests
import json
from typing import List, Dict, Iterator

class OllamaClient:
    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host
        self.session = requests.Session()

    def list_models(self) -> List[Dict]:
        """Возвращает список доступных моделей"""
        response = self.session.get(f"{self.host}/api/tags")
        response.raise_for_status()
        return response.json().get("models", [])

    def generate_stream(self, messages: List[Dict], model: str) -> Iterator[Dict]:
        """Генерирует ответ в streaming режиме"""
        payload = {"model": model, "messages": messages, "stream": True}
        response = self.session.post(
            f"{self.host}/api/chat",
            json=payload,
            stream=True
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                yield json.loads(line)
```

**app/history.py:**
```python
from datetime import datetime
from typing import List, Dict

class SessionHistory:
    def __init__(self):
        self.messages: List[Dict] = []

    def add_user_message(self, content: str) -> None:
        self.messages.append({
            "role": "user",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def add_assistant_message(self, content: str) -> None:
        self.messages.append({
            "role": "assistant",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def get_for_api(self) -> List[Dict]:
        """Возвращает в формате Ollama API"""
        return [{"role": m["role"], "content": m["content"]} for m in self.messages]
```

**app/chainlit_app.py:**
```python
import chainlit as cl
from app.ollama_client import OllamaClient
from app.history import SessionHistory
import time
import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

@cl.on_chat_start
async def on_chat_start():
    try:
        client = OllamaClient(OLLAMA_HOST)
        models = client.list_models()

        if not models:
            await cl.Message(
                content="❌ Моделей нет. Установите: `ollama pull gemma2:2b`"
            ).send()
            return

        settings = await cl.ChatSettings(
            [
                cl.input_widget.Select(
                    id="model",
                    label="Выберите модель",
                    values=[m["name"] for m in models],
                    initial_index=0
                )
            ]
        ).send()

        model = settings["model"]
        history = SessionHistory()

        cl.user_session.set("model", model)
        cl.user_session.set("history", history)
        cl.user_session.set("client", client)

        await cl.Message(
            content=f"✅ Подключено к {model}. Отправьте сообщение!"
        ).send()

    except Exception as e:
        await cl.Message(content=f"❌ Ошибка: {e}").send()

@cl.on_message
async def on_message(message: cl.Message):
    history = cl.user_session.get("history")
    client = cl.user_session.get("client")
    model = cl.user_session.get("model")

    history.add_user_message(message.content)

    start_time = time.time()
    response_content = ""

    msg = cl.Message(content="")
    await msg.send()

    for chunk in client.generate_stream(history.get_for_api(), model):
        if "message" in chunk:
            token = chunk["message"].get("content", "")
            response_content += token
            await msg.stream_token(token)

    duration = time.time() - start_time

    metrics = f"\n\n⏱ {duration:.1f} сек • 🔢 {len(response_content)} символов"
    await msg.stream_token(metrics)

    history.add_assistant_message(response_content)
```

**Зависимости (requirements.txt):**
```
chainlit==2.3.0
requests==2.32.3
python-dotenv==1.0.1
```

## Тестирование

1. Установить и запустить Ollama:
   ```bash
   brew install ollama  # macOS
   ollama serve
   ollama pull gemma2:2b
   ```

2. Установить зависимости:
   ```bash
   pip install -r requirements.txt
   ```

3. Запустить приложение:
   ```bash
   chainlit run app/chainlit_app.py
   ```

4. Открыть http://localhost:8000

5. Проверить:
   - Выбор модели из dropdown
   - Отправка сообщения
   - Stream вывод ответа
   - Метрики под ответом
   - История в UI
