# day1 — qwen2.5:3b

- Время (wall): **19.6s**
- Токенов в ответе: **309**
- Скорость: **119.9 tok/s**

## Промпт

```
Добавь в `app.py` новую команду `/history` — показывает последние 10 сообщений
пользователя из текущей сессии (хранение через `cl.user_session.get("history")`).
Следуй правилам CLAUDE.md из system prompt: паттерн команды, без эмодзи,
без новых папок, без выдуманных API. Верни полностью файл handler-функции
и строку регистрации команды в on_message.
```

## Ответ модели

Конечно! Добавлю новую команду `/history` для показа последних 10 сообщений пользователя из текущей сессии.

### Изменения в `app.py`

```python
from fastapi import APIRouter, Request
import chainlit as cl

router = APIRouter()

@cl.on_chat_message
async def on_message(message: str, request: Request):
    # Паттерн команды
    if message == "/history":
        await handle_history()
        return
    
    # Другие хендлеры...
    
async def handle_history():
    user_session = cl.user_session.get()
    history = user_session.get("history", [])
    
    # Если история меньше 10 сообщений, добавляем последние
    if len(history) < 10:
        history.extend(user_session["messages"][-10:])
    
    # Показываем последние 10 сообщений
    for i, msg in enumerate(history):
        if i >= 10: 
            break
        await cl.append_message(request.response, 
                                 message=msg,
                                 **cl.user_session.get("assistant", {}))
```

### Регистрация команды в `on_message`

```python
@router.post("/api/conversation")
async def on_message_handler(request: Request):
    return await on_message(await request.json())
```

Теперь команда `/history` будет показывать последние 10 сообщений пользователя из текущей сессии.
