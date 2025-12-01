import chainlit as cl
from app.langchain_client import build_chain


@cl.on_chat_start
async def on_chat_start():
    try:
        chain = build_chain()
    except Exception as exc:
        await cl.Message(content=f"Не удалось инициализировать LLM: {exc}").send()
        return

    cl.user_session.set("chain", chain)
    await cl.Message(
        content=(
            "🎄 AI Advent Challenge — Задание 1\n\n"
            "Прокси к OpenRouter готов! "
            "Используется **Grok 4.1 Fast** (бесплатно до 3 декабря 2025).\n\n"
            "Напишите сообщение — я передам его модели через LangChain."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    chain = cl.user_session.get("chain")
    if not chain:
        await cl.Message(
            content="LLM не инициализирован. Перезапустите чат после установки API-ключа."
        ).send()
        return

    response_text = await chain.ainvoke({"input": message.content})
    await cl.Message(content=response_text).send()
