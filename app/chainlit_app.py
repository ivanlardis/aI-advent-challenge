import logging
import os
from typing import Any, Dict, List

import chainlit as cl

from app.openrouter_client import OpenRouterClient, build_messages

DEFAULT_SYSTEM_PROMPT = os.getenv("DEFAULT_SYSTEM_PROMPT", "")

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def format_history_for_summary(history: List[Dict[str, str]]) -> str:
    """Преобразует историю в компактный текст для сжатия."""
    formatted = []
    for idx, item in enumerate(history, 1):
        role = "Пользователь" if item["role"] == "user" else "Ассистент"
        formatted.append(f"{idx}. {role}: {item['content']}")
    return "\n".join(formatted)


def shorten_text(text: str, limit: int = 80) -> str:
    """Укорачивает текст до нужной длины для таблиц отчёта."""
    single_line = " ".join(text.split())
    if len(single_line) <= limit:
        return single_line
    return single_line[: limit - 1] + "…"


def format_usage_summary(usage_history: List[Dict[str, Any]]) -> str:
    """Готовит Markdown-отчёт по токенам за диалог."""
    total_prompt = sum(item.get("prompt_tokens", 0) for item in usage_history)
    total_completion = sum(item.get("completion_tokens", 0) for item in usage_history)
    total_tokens = sum(item.get("total_tokens", 0) for item in usage_history)

    lines = [
        "📊 **Статистика токенов по диалогу**\n",
        "| # | Пользователь | prompt | completion | total | ctx msgs | user len | assistant len | system len |",
        "|---|--------------|--------|------------|-------|----------|----------|---------------|------------|",
    ]

    for idx, item in enumerate(usage_history, 1):
        user_preview = shorten_text(item.get("user_message", ""), 70)
        lines.append(
            f"| {idx} | {user_preview} | "
            f"{item.get('prompt_tokens', 0)} | "
            f"{item.get('completion_tokens', 0)} | "
            f"{item.get('total_tokens', 0)} | "
            f"{item.get('history_messages', 0)} | "
            f"{item.get('user_length', 0)} | "
            f"{item.get('assistant_length', 0)} | "
            f"{item.get('system_length', 0)} |"
        )

    lines.append("")
    lines.append(
        f"**Итого:** prompt {total_prompt} · completion {total_completion} · total {total_tokens} токенов"
    )

    return "\n".join(lines)


async def handle_compress_command(message: cl.Message):
    """Сжимает историю диалога в краткую сводку и заменяет историю."""
    client = cl.user_session.get("client")
    if not client:
        await cl.Message(content="OpenRouter клиент не инициализирован.").send()
        return

    history = cl.user_session.get("history", [])
    if not history:
        await cl.Message(content="ℹ️ История пуста — сжимать нечего.").send()
        return

    logger.info("Command /compress: history_messages=%d", len(history))
    await cl.Message(content="🗜️ Сжимаю историю диалога, это займёт пару секунд...").send()

    compression_prompt = (
        "Ты помогаешь сжимать длинные диалоги для продолжения общения.\n"
        "Сделай краткую, насыщенную фактами сводку: ключевые вводные пользователя, "
        "задания, ограничения, решения ассистента. Без воды и новых рекомендаций."
    )

    formatted_history = format_history_for_summary(history)
    messages = [
        {"role": "system", "content": compression_prompt},
        {
            "role": "user",
            "content": (
                "Сожми историю ниже в 6-10 предложений или пунктов, сохранив все важные факты.\n\n"
                f"{formatted_history}"
            ),
        },
    ]

    try:
        summary_text = await client.get_completion_text(messages, temperature=0.2)

        compressed_history = [
            {
                "role": "assistant",
                "content": f"Краткая сводка предыдущего диалога: {summary_text.strip()}",
            }
        ]
        cl.user_session.set("history", compressed_history)
        logger.info("Command /compress completed. Summary_length=%d", len(summary_text))

        await cl.Message(
            content=(
                "✅ История сжата и заменена краткой сводкой.\n\n"
                f"{compressed_history[0]['content']}"
            )
        ).send()
    except Exception as e:
        logger.exception("Command /compress failed")
        await cl.Message(content=f"❌ Не удалось сжать историю: {e}").send()


async def handle_usage_summary_command():
    """Выводит отчёт по использованным токенам в диалоге."""
    usage_history = cl.user_session.get("usage_history", [])
    if not usage_history:
        await cl.Message(content="ℹ️ Пока нет данных по токенам — ещё не было запросов.").send()
        return

    logger.info("Command /summary: items=%d", len(usage_history))

    report = format_usage_summary(usage_history)
    await cl.Message(content=report).send()


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("history", [])
    cl.user_session.set("usage_history", [])
    logger.info("Chat started: history initialized")

    try:
        client = OpenRouterClient()
    except Exception as exc:
        await cl.Message(content=f"Не удалось инициализировать OpenRouter клиент: {exc}").send()
        return

    cl.user_session.set("client", client)

    model_name = os.getenv("OPENROUTER_MODEL", "tngtech/deepseek-r1t2-chimera:free")
    await cl.Message(
        content=(
            "🤖 Чат ассистента. Доступные команды:\n\n"
            "• `/compress` — сжимает текущую историю в краткую сводку\n"
            "• `/summary` — выводит статистику по токенам за диалог\n\n"
            "Остальное — обычный диалог без system prompt "
            f"(можно задать через переменную `DEFAULT_SYSTEM_PROMPT`).\n\n"
            f"_Модель: {model_name}_"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    logger.info(
        "Incoming message len=%d startswith=%s",
        len(message.content),
        message.content[:20].replace("\n", " "),
    )

    if message.content.strip().startswith("/compress"):
        await handle_compress_command(message)
        return

    if message.content.strip().startswith("/summary"):
        await handle_usage_summary_command()
        return

    client = cl.user_session.get("client")
    if not client:
        await cl.Message(
            content="OpenRouter клиент не инициализирован. Перезапустите чат после установки API-ключа."
        ).send()
        return

    history = cl.user_session.get("history", [])
    system_prompt = DEFAULT_SYSTEM_PROMPT
    logger.info(
        "Normal chat message: history_len=%d system_prompt=%s",
        len(history),
        "custom" if system_prompt else "none",
    )
    history_len_before = len(history)
    system_len = len(system_prompt)
    user_len = len(message.content)

    try:
        messages = build_messages(message.content, history, system_prompt)
        result = await client.chat_completion(messages)
        usage = result.get("usage", {})
        assistant_content = result["choices"][0]["message"]["content"]
        assistant_len = len(assistant_content)

        await cl.Message(content=assistant_content).send()

        history.append({"role": "user", "content": message.content})
        history.append({"role": "assistant", "content": assistant_content})
        cl.user_session.set("history", history)

        usage_history = cl.user_session.get("usage_history", [])
        usage_history.append(
            {
                "user_message": message.content,
                "assistant_message": assistant_content,
                "prompt_tokens": usage.get("prompt_tokens", 0) if usage else 0,
                "completion_tokens": usage.get("completion_tokens", 0) if usage else 0,
                "total_tokens": usage.get("total_tokens", 0) if usage else 0,
                "history_messages": history_len_before,
                "user_length": user_len,
                "assistant_length": assistant_len,
                "system_length": system_len,
            }
        )
        cl.user_session.set("usage_history", usage_history)
        logger.info(
            "Message processed: prompt=%s completion=%s total=%s",
            usage.get("prompt_tokens", 0) if usage else 0,
            usage.get("completion_tokens", 0) if usage else 0,
            usage.get("total_tokens", 0) if usage else 0,
        )

    except Exception as e:
        logger.exception("Error handling message")
        await cl.Message(
            content=f"❌ Ошибка обработки ответа: {e}\n\nПопробуйте переформулировать запрос."
        ).send()
