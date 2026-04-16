"""Тесты для lib/history.py."""

from lib.history import trim_history, estimate_tokens


def test_trim_preserves_system():
    """System prompt должен оставаться в истории после обрезки."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello, how can I help?"},
        {"role": "user", "content": "Tell me a story about a brave knight."},
    ]

    result = trim_history(messages, max_tokens=20)

    system_messages = [m for m in result if m["role"] == "system"]
    assert len(system_messages) == 1, (
        "System prompt должен сохраняться при обрезке истории, "
        f"но в результате нет роли 'system'. Результат: {result}"
    )


def test_trim_uses_token_estimation_not_chars():
    """estimate_tokens должен оценивать токены, а не символы.

    Правило: ~1 токен = 1 слово (грубо). Сообщение 'one two three'
    это 3 токена, а не 13 символов.
    """
    messages = [{"role": "user", "content": "one two three"}]

    result = trim_history(messages, max_tokens=10)

    assert len(result) == 1, (
        "Сообщение из 3 слов должно помещаться в лимит 10 токенов. "
        f"estimate_tokens завышает оценку. Результат: {result}"
    )


def test_estimate_tokens_returns_word_count_approximately():
    """estimate_tokens должен возвращать приблизительно количество слов."""
    assert estimate_tokens("hello world") <= 3, (
        "Два слова должны давать не больше ~3 токенов"
    )
