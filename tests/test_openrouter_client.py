"""Тесты для lib/openrouter_client.build_messages."""

from lib.openrouter_client import build_messages


def test_build_messages_without_system_prompt():
    messages = build_messages("hello", [], "")
    assert messages == [{"role": "user", "content": "hello"}]


def test_build_messages_with_system_prompt():
    messages = build_messages("hello", [], "You are helpful")
    assert messages[0] == {"role": "system", "content": "You are helpful"}
    assert messages[-1] == {"role": "user", "content": "hello"}


def test_build_messages_preserves_history_order():
    history = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "reply"},
    ]
    messages = build_messages("next", history, "sys")
    assert [m["content"] for m in messages] == ["sys", "first", "reply", "next"]


def test_build_messages_user_input_always_last():
    history = [{"role": "assistant", "content": "a"}]
    messages = build_messages("q", history)
    assert messages[-1] == {"role": "user", "content": "q"}
