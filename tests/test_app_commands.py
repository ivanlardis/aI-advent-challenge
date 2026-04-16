"""Тесты для роутера команд в app.py (unit-уровень, без Chainlit UI)."""

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
    ):
        assert hasattr(app, name), f"app.py должен экспортировать {name}"


def test_non_slash_is_not_command():
    user_input = "привет /dashboard внутри"
    cmd = user_input.strip().split()[0].lower()
    assert not cmd.startswith("/")
