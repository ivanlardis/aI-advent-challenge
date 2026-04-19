"""Тесты для роутера команд в app.py (unit-уровень, без Chainlit UI)."""

import asyncio
import importlib


def test_command_detection_slash_prefix():
    """Паттерн: команда всегда начинается с / и разбирается через split()[0].lower()."""
    cases = [
        ("/dashboard", "/dashboard"),
        ("/Summary", "/summary"),
        ("/compress now", "/compress"),
        ("/profile   ", "/profile"),
        ("/reset", "/reset"),
    ]
    for user_input, expected in cases:
        cmd = user_input.strip().split()[0].lower()
        assert cmd == expected


def test_app_module_exposes_command_handlers():
    """app.py должен экспортировать все хендлеры команд (для тестируемости и скилла)."""
    app = importlib.import_module("app")
    for name in (
        "handle_compress_command",
        "handle_summary_command",
        "handle_dashboard_command",
        "handle_profile_command",
        "handle_reset_command",
        "handle_help_command",
        "format_help",
        "handle_version_command",
    ):
        assert hasattr(app, name), f"app.py должен экспортировать {name}"


def test_format_help_contains_all_commands():
    """format_help() должен перечислить все команды проекта."""
    import importlib
    app = importlib.import_module("app")
    help_text = app.format_help()
    for cmd in ("/help", "/compress", "/summary", "/dashboard", "/profile", "/reset"):
        assert cmd in help_text, f"В справке нет {cmd}"


def test_non_slash_is_not_command():
    user_input = "привет /dashboard внутри"
    cmd = user_input.strip().split()[0].lower()
    assert not cmd.startswith("/")


def test_clear_is_alias_for_reset():
    """Команды /clear и /reset обе распарсятся и попадут в один хендлер."""
    import importlib
    import inspect

    app = importlib.import_module("app")
    source = inspect.getsource(app.on_message)
    assert "/clear" in source, "В роутере должна быть обработка /clear"
    assert '("/reset", "/clear")' in source or '"/clear", "/reset"' in source, \
        "/clear должен маршрутизироваться в ту же ветку, что и /reset"


def test_handle_summary_command_aggregates_total_tokens(monkeypatch):
    """handle_summary_command должен суммировать 'total_tokens' из usage_history
    (ключ, который реально пишет Analytics.record_usage)."""
    app = importlib.import_module("app")

    sent_messages = []

    class FakeMessage:
        def __init__(self, content=""):
            self.content = content

        async def send(self):
            sent_messages.append(self.content)

    monkeypatch.setattr(app.cl, "Message", FakeMessage)

    usage_history = [
        {"total_tokens": 10, "prompt_tokens": 6, "completion_tokens": 4, "input_preview": "hi"},
        {"total_tokens": 25, "prompt_tokens": 15, "completion_tokens": 10, "input_preview": "hello"},
        {"total_tokens": 5, "prompt_tokens": 3, "completion_tokens": 2, "input_preview": "hey"},
    ]

    asyncio.run(app.handle_summary_command(usage_history))

    assert len(sent_messages) == 1
    output = sent_messages[0]
    # Сумма 10 + 25 + 5 = 40
    assert "40" in output, f"Ожидали суммарные 40 токенов в выводе, получили: {output}"
    # Отдельные значения тоже должны присутствовать
    assert "10" in output
    assert "25" in output


def test_handle_summary_command_empty_history(monkeypatch):
    """При пустой истории должно выводиться сообщение-заглушка, а не падать."""
    app = importlib.import_module("app")

    sent_messages = []

    class FakeMessage:
        def __init__(self, content=""):
            self.content = content

        async def send(self):
            sent_messages.append(self.content)

    monkeypatch.setattr(app.cl, "Message", FakeMessage)

    asyncio.run(app.handle_summary_command([]))

    assert len(sent_messages) == 1
    assert "нет данных" in sent_messages[0].lower()
