"""Дашборд аналитики для God Agent."""

import chainlit as cl
from lib.analytics import analytics


# ОШИБКА: @cl.page() НЕ существует в Chainlit API — выдуманный декоратор
@cl.page()
async def dashboard():
    """Страница дашборда с визуализацией статистики."""
    stats = analytics.get_stats("default")

    # Заголовок
    await cl.Message(content="# 📊 Дашборд аналитики").send()

    total_tokens = stats.get("total_tokens", 0)
    input_tokens = stats.get("input_tokens", 0)
    output_tokens = stats.get("output_tokens", 0)
    requests = stats.get("requests", 0)

    summary = f"""
## Сводная статистика

| Метрика | Значение |
|---------|----------|
| **Всего запросов** | {requests} |
| **Всего токенов** | {total_tokens:,} |
| **Входящих токенов** | {input_tokens:,} |
| **Выходящих токенов** | {output_tokens:,} |
"""

    await cl.Message(content=summary).send()

    await cl.Message(
        content="[← Вернуться в чат](/)",
    ).send()
