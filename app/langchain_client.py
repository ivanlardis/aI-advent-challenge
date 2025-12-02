import os

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


def build_chain():
    """Создает LangChain-цепочку для анализа настроения с JSON-выводом."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Установите OPENROUTER_API_KEY, чтобы обратиться к OpenRouter.")

    model = os.getenv("OPENROUTER_MODEL", "tngtech/deepseek-r1t2-chimera:free")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=0.3,
    )

    # Создаём JSON parser
    parser = JsonOutputParser()

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Ты — помощник для анализа настроения текста.\n\n"
                "{format_instructions}\n\n"
                "Всегда возвращай JSON с полями:\n"
                '- sentiment: "positive", "negative" или "neutral"\n'
                "- confidence: число от 0 до 1\n"
                "- keywords: массив ключевых слов\n"
                "- summary: краткое объяснение анализа"
            ),
            ("human", "{input}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    # Цепочка с JsonOutputParser
    return prompt | llm | parser
