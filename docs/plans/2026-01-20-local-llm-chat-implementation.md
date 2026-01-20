# Local LLM Chat Application Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Создать Chainlit приложение с интеграцией локальной LLM (Ollama), сессионной историей диалога, выбором модели и метриками генерации.

**Architecture:** Chainlit веб-интерфейс с Python backend, прямые HTTP запросы к Ollama API через библиотеку requests, сессионное хранение истории в памяти, stream вывод ответов.

**Tech Stack:** Python 3.10+, Chainlit 2.3.0, requests, Ollama API, Docker (опционально для Ollama)

---

## Task 1: Создать структуру директорий

**Files:**
- Create: `app/__init__.py`
- Create: `app/ollama_client.py`
- Create: `app/history.py`
- Create: `app/chainlit_app.py`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `README.md`

**Step 1: Create app directory with __init__.py**

```bash
mkdir -p app
touch app/__init__.py
```

**Step 2: Verify structure**

Run: `ls -la app/`
Expected: `__init__.py` exists

**Step 3: Commit**

```bash
git add app/__init__.py
git commit -m "feat: create app directory structure"
```

---

## Task 2: Создать requirements.txt

**Files:**
- Create: `requirements.txt`

**Step 1: Write requirements.txt**

```bash
cat > requirements.txt << 'EOF'
chainlit==2.3.0
requests==2.32.3
python-dotenv==1.0.1
EOF
```

**Step 2: Verify file content**

Run: `cat requirements.txt`
Expected: Shows three dependencies with exact versions

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "deps: add chainlit, requests and python-dotenv"
```

---

## Task 3: Создать .env.example

**Files:**
- Create: `.env.example`

**Step 1: Write .env.example**

```bash
cat > .env.example << 'EOF'
# Ollama configuration
OLLAMA_HOST=http://localhost:11434
EOF
```

**Step 2: Verify file content**

Run: `cat .env.example`
Expected: Shows OLLAMA_HOST configuration example

**Step 3: Commit**

```bash
git add .env.example
git commit -m "config: add environment variables example"
```

---

## Task 4: Создать OllamaClient класс

**Files:**
- Create: `app/ollama_client.py`

**Step 1: Write OllamaClient implementation**

```python
import requests
import json
from typing import List, Dict, Iterator


class OllamaClient:
    """HTTP клиент для Ollama API."""

    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host
        self.session = requests.Session()

    def list_models(self) -> List[Dict]:
        """Возвращает список доступных моделей.

        Returns:
            Список словарей с информацией о моделях

        Raises:
            requests.RequestException: При ошибке подключения
        """
        response = self.session.get(f"{self.host}/api/tags")
        response.raise_for_status()
        return response.json().get("models", [])

    def generate_stream(self, messages: List[Dict], model: str) -> Iterator[Dict]:
        """Генерирует ответ в streaming режиме.

        Args:
            messages: История сообщений в формате Ollama API
            model: Название модели

        Yields:
            Чанки ответа от Ollama API

        Raises:
            requests.RequestException: При ошибке генерации
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }

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

**Step 2: Verify syntax**

Run: `python -m py_compile app/ollama_client.py`
Expected: No errors

**Step 3: Commit**

```bash
git add app/ollama_client.py
git commit -m "feat: add OllamaClient with list_models and generate_stream"
```

---

## Task 5: Создать SessionHistory класс

**Files:**
- Create: `app/history.py`

**Step 1: Write SessionHistory implementation**

```python
from datetime import datetime
from typing import List, Dict


class SessionHistory:
    """Менеджер сессионной истории сообщений."""

    def __init__(self):
        self.messages: List[Dict] = []

    def add_user_message(self, content: str) -> None:
        """Добавляет сообщение пользователя в историю.

        Args:
            content: Текст сообщения
        """
        self.messages.append({
            "role": "user",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def add_assistant_message(self, content: str) -> None:
        """Добавляет ответ ассистента в историю.

        Args:
            content: Текст ответа
        """
        self.messages.append({
            "role": "assistant",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def get_for_api(self) -> List[Dict]:
        """Возвращает историю в формате Ollama API.

        Returns:
            Список сообщений с полями role и content
        """
        return [
            {"role": m["role"], "content": m["content"]}
            for m in self.messages
        ]

    def clear(self) -> None:
        """Очищает историю сообщений."""
        self.messages.clear()
```

**Step 2: Verify syntax**

Run: `python -m py_compile app/history.py`
Expected: No errors

**Step 3: Commit**

```bash
git add app/history.py
git commit -m "feat: add SessionHistory for managing chat history"
```

---

## Task 6: Создать Chainlit приложение

**Files:**
- Create: `app/chainlit_app.py`

**Step 1: Write chainlit_app.py implementation**

```python
import chainlit as cl
from app.ollama_client import OllamaClient
from app.history import SessionHistory
import time
import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


@cl.on_chat_start
async def on_chat_start():
    """Обработчик начала чата: подключение к Ollama и выбор модели."""
    try:
        client = OllamaClient(OLLAMA_HOST)
        models = client.list_models()

        if not models:
            await cl.Message(
                content=(
                    "❌ Модели не найдены.\n\n"
                    "Установите модель:\n"
                    "```bash\nollama pull gemma2:2b\n```\n\n"
                    "Или запустите Ollama:\n"
                    "```bash\nollama serve\n```"
                )
            ).send()
            return

        # Dropdown для выбора модели
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
            content=f"✅ Подключено к **{model}**\n\nОтправьте сообщение!"
        ).send()

    except requests.exceptions.ConnectionError:
        await cl.Message(
            content=(
                "❌ Ollama не запущен.\n\n"
                "Запустите Ollama:\n"
                "```bash\nollama serve\n```"
            )
        ).send()
    except Exception as e:
        await cl.Message(content=f"❌ Ошибка: {e}").send()


@cl.on_message
async def on_message(message: cl.Message):
    """Обработчик сообщения пользователя: генерация ответа с метриками."""
    history = cl.user_session.get("history")
    client = cl.user_session.get("client")
    model = cl.user_session.get("model")

    history.add_user_message(message.content)

    start_time = time.time()
    response_content = ""

    msg = cl.Message(content="")
    await msg.send()

    try:
        for chunk in client.generate_stream(history.get_for_api(), model):
            if "message" in chunk:
                token = chunk["message"].get("content", "")
                response_content += token
                await msg.stream_token(token)

        duration = time.time() - start_time
        char_count = len(response_content)

        metrics = (
            f"\n\n---\n"
            f"⏱ {duration:.1f} сек • 🔢 {char_count} символов"
        )
        await msg.stream_token(metrics)

        history.add_assistant_message(response_content)

    except Exception as e:
        await msg.stream_token(f"\n\n❌ Ошибка: {e}")


@cl.on_chat_end
async def on_chat_end():
    """Обработчик окончания чата: очистка сессии."""
    history = cl.user_session.get("history")
    if history:
        history.clear()
```

**Step 2: Verify syntax**

Run: `python -m py_compile app/chainlit_app.py`
Expected: No errors

**Step 3: Commit**

```bash
git add app/chainlit_app.py
git commit -m "feat: add Chainlit app with chat handlers"
```

---

## Task 7: Создать README с инструкциями

**Files:**
- Create: `README.md`

**Step 1: Write README.md**

```markdown
# Local LLM Chat - Chainlit приложение

Chainlit приложение для работы с локальными LLM через Ollama.

## Возможности

- 🤖 Работа с локальными моделями через Ollama
- 💬 Сессионная история диалога
- 🎛 Выбор модели из списка доступных
- 📊 Метрики генерации (время, количество символов)
- ⚡ Stream вывод ответов в реальном времени

## Требования

- Python 3.10+
- Ollama (установить и запустить)

## Установка

### 1. Установка Ollama

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Установка модели

```bash
ollama pull gemma2:2b
```

Доступные модели: https://ollama.com/library

### 3. Запуск Ollama

```bash
ollama serve
```

### 4. Установка зависимостей Python

```bash
pip install -r requirements.txt
```

## Использование

### 1. Настройка (опционально)

Скопируйте `.env.example` в `.env` и измените хост Ollama если нужно:

```bash
cp .env.example .env
```

### 2. Запуск приложения

```bash
chainlit run app/chainlit_app.py
```

### 3. Открытие в браузере

Откройте http://localhost:8000

## Структура проекта

```
.
├── app/
│   ├── __init__.py
│   ├── chainlit_app.py    # Главный файл Chainlit
│   ├── ollama_client.py   # HTTP клиент для Ollama
│   └── history.py         # Менеджер истории
├── requirements.txt
├── .env.example
└── README.md
```

## API Ollama

Приложение использует Ollama API:
- `GET /api/tags` - список моделей
- `POST /api/chat` - генерация ответа

Документация: https://github.com/ollama/ollama/blob/main/docs/api.md

## AI Advent Challenge 2025

День 26: Встроить локальную LLM в приложение.
```

**Step 2: Verify file content**

Run: `head -30 README.md`
Expected: Shows title and features

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add README with installation and usage instructions"
```

---

## Task 8: Создать .gitignore

**Files:**
- Create: `.gitignore`

**Step 1: Write .gitignore**

```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv

# Environment
.env

# Chainlit
.chainlit/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
EOF
```

**Step 2: Verify file content**

Run: `cat .gitignore`
Expected: Shows Python, venv, .env, and IDE ignores

**Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: add gitignore for Python project"
```

---

## Task 9: Ручное тестирование приложения

**Files:**
- None (manual testing)

**Step 1: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages install successfully

**Step 2: Ensure Ollama is running**

```bash
ollama list
```

Expected: Shows at least one installed model

If no models: `ollama pull gemma2:2b`

**Step 3: Start the application**

```bash
chainlit run app/chainlit_app.py -w
```

Expected: Server starts on http://localhost:8000

Flag `-w` enables auto-reload on code changes

**Step 4: Test in browser**

1. Open http://localhost:8000
2. Select model from dropdown
3. Send message: "Привет! Расскажи о себе."
4. Verify:
   - Stream output appears in real-time
   - Metrics shown below response (⏱ time • 🔢 characters)
   - Send follow-up message to test history
   - Context is maintained in conversation

**Step 5: Test error handling**

Stop Ollama: `pkill ollama`

Refresh browser and verify error message appears

Start Ollama again: `ollama serve`

**Step 6: Commit final version**

```bash
git add .
git commit -m "test: manual testing complete - application working"
```

---

## Task 10: Создать .chainlit/config.toml для кастомизации

**Files:**
- Create: `.chainlit/config.toml`

**Step 1: Create .chainlit directory and config**

```bash
mkdir -p .chainlit
cat > .chainlit/config.toml << 'EOF'
[UI]
# Название приложения
name = "Local LLM Chat"

# Описание
description = "Чат с локальными LLM через Ollama"

# Иконка (по умолчанию Chainlit)
# default_collapse_message = false

[project]
# Информация о проекте
# theme = "default"
EOF
```

**Step 2: Verify directory structure**

Run: `ls -la .chainlit/`
Expected: `config.toml` exists

**Step 3: Commit**

```bash
git add .chainlit/config.toml
git commit -m "feat: add Chainlit configuration"
```

---

## Задания для тестирования (если требуется)

Если нужно добавить автоматические тесты:

1. **Тест OllamaClient**: мокировать requests.Session и проверять вызовы API
2. **Тест SessionHistory**: проверять добавление сообщений и формат для API
3. **Интеграционные тесты**: запускать Chainlit с тестовым Ollama server

Для Day 26 достаточно ручного тестирования.

---

## Финальная проверка

**Step 1: Verify all files exist**

```bash
find . -type f -name "*.py" -o -name "*.txt" -o -name "*.md" -o -name ".env.example" | grep -v ".git" | sort
```

Expected:
```
.app/__init__.py
.app/chainlit_app.py
.app/history.py
.app/ollama_client.py
.chainlit/config.toml
.env.example
.gitignore
README.md
requirements.txt
```

**Step 2: Verify git log**

```bash
git log --oneline -10
```

Expected: Series of commits with proper messages

**Step 3: Final commit if needed**

```bash
git add .
git commit -m "feat: complete local LLM chat application for Day 26"
```

---

## Использование этого плана

Этот план готов к реализации. Используйте супернавык `superpowers:executing-plans` для пошагового выполнения.

Каждая задача разбита на минимальные шаги:
1. Написать код/тест
2. Проверить (команда проверки)
3. Закоммитить

DRY, YAGNI, TDD, частые коммиты.
