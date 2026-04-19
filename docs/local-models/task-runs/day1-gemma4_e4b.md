# day1 — gemma4:e4b

- Время (wall): **16.32s**
- Токенов в ответе: **760**
- Скорость: **66.0 tok/s**

## Промпт

```
Добавь в `app.py` новую команду `/history` — показывает последние 10 сообщений
пользователя из текущей сессии (хранение через `cl.user_session.get("history")`).
Следуй правилам CLAUDE.md из system prompt: паттерн команды, без эмодзи,
без новых папок, без выдуманных API. Верни полностью файл handler-функции
и строку регистрации команды в on_message.
```

## Ответ модели

**Файл:** `app.py`

### 1. Функция-обработчик

```python
async def handle_history(state: cl.ChatState) -> None:
    """
    Показывает последние 10 сообщений пользователя из текущей сессии.
    """
    history: list[str] = state.user_session.get("history", [])
    
    if not history:
        await cl.Message(content="История сообщений пуста.").send()
        return

    # Берем последние 10 сообщений
    recent_messages = history[-10:]
    
    output = "Последние 10 сообщений пользователя:\n"
    for i, message in enumerate(recent_messages):
        output += f"{i+1}. {message}\n"
        
    await cl.Message(content=output).send()
```

### 2. Регистрация команды в `on_message`

```python
# Внутри функции on_message:
if cmd == "/history":
    await handle_history(state)
    return
```
