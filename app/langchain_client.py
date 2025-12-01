import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


def build_chain():
    """Создает простую LangChain-цепочку, проксирующую запросы в OpenRouter."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Установите OPENROUTER_API_KEY, чтобы обратиться к OpenRouter.")

    model = os.getenv("OPENROUTER_MODEL", "x-ai/grok-4.1-fast:free")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=0.3,
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Ты — полезный помощник. Отвечай кратко, если не просят иначе.",
            ),
            ("human", "{input}"),
        ]
    )

    return prompt | llm | StrOutputParser()
