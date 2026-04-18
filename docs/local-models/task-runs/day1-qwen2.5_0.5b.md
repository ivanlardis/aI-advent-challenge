# day1 — qwen2.5:0.5b

- Время (wall): **1.79s**
- Токенов в ответе: **223**
- Скорость: **285.0 tok/s**

## Промпт

```
Добавь в `app.py` новую команду `/history` — показывает последние 10 сообщений
пользователя из текущей сессии (хранение через `cl.user_session.get("history")`).
Следуй правилам CLAUDE.md из system prompt: паттерн команды, без эмодзи,
без новых папок, без выдуманных API. Верни полностью файл handler-функции
и строку регистрации команды в on_message.
```

## Ответ модели

```python
from langchain import OpenRouter

# Создаем хендлер для истории сообщений
@app.route("/history", methods=["GET"])
def get_history():
    history = cl.user_session.get("history")
    if not history:
        return "No messages in the history.", 204

    # Загружаем последние 10 сообщения из истории
    last_10_messages = history[-10:]
    
    return f"Here are the last 10 messages: {last_10_messages}"

# Регистрируем команду /history в on_message
@app.on_message("/history")
def handle_history_command(message):
    # Получаем последние 10 сообщения из истории
    history = cl.user_session.get("history")
    if not history:
        return "No messages in the history."

    # Загружаем последние 10 сообщения из истории
    last_10_messages = history[-10:]

    return f"Here are the last 10 messages: {last_10_messages}"
```
