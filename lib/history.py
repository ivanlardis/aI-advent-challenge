"""История диалога: оценка размера и обрезка под лимит токенов."""

from typing import List, Dict


def estimate_tokens(text: str) -> int:
    """Грубая оценка количества токенов в тексте."""
    # Считаем символы как приближение токенов
    return len(text)


def trim_history(messages: List[Dict], max_tokens: int) -> List[Dict]:
    """
    Обрезает историю диалога под лимит токенов.
    Удаляет старые сообщения, пока суммарный размер не уложится в лимит.
    System prompt (первое сообщение с ролью "system") должен сохраняться.
    """
    total = sum(estimate_tokens(m["content"]) for m in messages)

    while total > max_tokens and messages:
        removed = messages.pop(0)
        total -= estimate_tokens(removed["content"])

    return messages
