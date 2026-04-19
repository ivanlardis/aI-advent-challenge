"""Тесты для lib/openrouter_client."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from lib.openrouter_client import OpenRouterClient, build_messages


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


def _make_client(monkeypatch):
    """Создаёт OpenRouterClient с замоканным ChatOpenAI."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    with patch("lib.openrouter_client.ChatOpenAI") as mock_chat:
        client = OpenRouterClient()
    return client, mock_chat


def test_chat_completion_passes_temperature_to_llm(monkeypatch):
    client, _ = _make_client(monkeypatch)

    bound_llm = MagicMock()
    bound_llm.ainvoke = AsyncMock(
        return_value=SimpleNamespace(content="ok", usage_metadata={})
    )
    client.llm = MagicMock()
    client.llm.bind = MagicMock(return_value=bound_llm)

    result = asyncio.run(
        client.chat_completion(
            [{"role": "user", "content": "hi"}], temperature=0.7
        )
    )

    client.llm.bind.assert_called_once_with(temperature=0.7)
    bound_llm.ainvoke.assert_awaited_once()
    assert result["choices"][0]["message"]["content"] == "ok"


def test_chat_completion_default_temperature(monkeypatch):
    client, _ = _make_client(monkeypatch)

    bound_llm = MagicMock()
    bound_llm.ainvoke = AsyncMock(
        return_value=SimpleNamespace(content="ok", usage_metadata={})
    )
    client.llm = MagicMock()
    client.llm.bind = MagicMock(return_value=bound_llm)

    asyncio.run(client.chat_completion([{"role": "user", "content": "hi"}]))

    client.llm.bind.assert_called_once_with(temperature=0.3)


def test_stream_completion_passes_temperature_to_llm(monkeypatch):
    client, _ = _make_client(monkeypatch)

    async def fake_astream(_messages):
        for piece in ("a", "b"):
            yield SimpleNamespace(content=piece)

    bound_llm = MagicMock()
    bound_llm.astream = fake_astream
    client.llm = MagicMock()
    client.llm.bind = MagicMock(return_value=bound_llm)

    async def collect():
        return [
            chunk
            async for chunk in client.stream_completion(
                [{"role": "user", "content": "hi"}], temperature=0.9
            )
        ]

    chunks = asyncio.run(collect())

    client.llm.bind.assert_called_once_with(temperature=0.9)
    assert chunks == ["a", "b"]
