"""История диалога: оценка размера и обрезка под лимит токенов."""

from typing import List, Dict


def estimate_tokens(text: str) -> int:
    """Грубая оценка количества токенов в тексте (~1 токен = 1 слово)."""
    return len(text.split())


def trim_history(messages: List[Dict], max_tokens: int) -> List[Dict]:
    """
    Обрезает историю диалога под лимит токенов.
    Удаляет старые сообщения, пока суммарный размер не уложится в лимит.
    System prompt (сообщения с ролью "system") сохраняются и не удаляются.
    """
    total = sum(estimate_tokens(m["content"]) for m in messages)

    # Индекс первого не-system сообщения, которое можно удалить.
    i = 0
    while total > max_tokens and i < len(messages):
        if messages[i]["role"] == "system":
            i += 1
            continue
        removed = messages.pop(i)
        total -= estimate_tokens(removed["content"])

    return messages
