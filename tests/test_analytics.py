"""Тесты для lib/analytics.py."""

from lib.analytics import Analytics


def test_record_usage_creates_new_list_when_none():
    result = Analytics.record_usage("hi", "hello", None, None)
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["user_input_length"] == 2
    assert result[0]["response_length"] == 5


def test_record_usage_appends_to_existing_list():
    existing = [{"total_tokens": 5}]
    result = Analytics.record_usage("q", "a", None, existing)
    assert len(result) == 2
    assert result is existing


def test_record_usage_uses_usage_data_when_provided():
    usage = {"prompt_tokens": 100, "completion_tokens": 50}
    result = Analytics.record_usage("q", "a", usage, None)
    assert result[0]["prompt_tokens"] == 100
    assert result[0]["completion_tokens"] == 50
    assert result[0]["total_tokens"] == 150


def test_record_usage_estimates_tokens_without_usage_data():
    text = "x" * 40
    result = Analytics.record_usage(text, text, None, None)
    assert result[0]["prompt_tokens"] == 10
    assert result[0]["completion_tokens"] == 10


def test_record_usage_truncates_preview():
    long_text = "a" * 100
    result = Analytics.record_usage(long_text, "a", None, None)
    assert result[0]["input_preview"].endswith("...")
    assert len(result[0]["input_preview"]) <= 43


def test_format_dashboard_empty():
    out = Analytics.format_dashboard([])
    assert "нет данных" in out.lower()


def test_format_dashboard_with_records():
    records = [
        {"total_tokens": 10, "prompt_tokens": 6, "completion_tokens": 4, "input_preview": "hi"},
        {"total_tokens": 20, "prompt_tokens": 12, "completion_tokens": 8, "input_preview": "hello"},
    ]
    out = Analytics.format_dashboard(records)
    assert "30" in out
    assert "Всего сообщений" in out


def test_format_dashboard_shows_avg_response_length():
    """Дашборд должен показывать среднюю длину ответа в символах."""
    records = [
        {"total_tokens": 10, "prompt_tokens": 6, "completion_tokens": 4,
         "input_preview": "hi", "response_length": 100},
        {"total_tokens": 20, "prompt_tokens": 12, "completion_tokens": 8,
         "input_preview": "hello", "response_length": 200},
    ]
    out = Analytics.format_dashboard(records)
    assert "Средняя длина ответа" in out
    assert "150" in out


def test_get_stats_empty():
    stats = Analytics.get_stats([])
    assert stats["message_count"] == 0
    assert stats["total_tokens"] == 0


def test_get_stats_aggregates():
    records = [
        {"total_tokens": 10, "prompt_tokens": 6, "completion_tokens": 4},
        {"total_tokens": 30, "prompt_tokens": 20, "completion_tokens": 10},
    ]
    stats = Analytics.get_stats(records)
    assert stats["message_count"] == 2
    assert stats["total_tokens"] == 40
    assert stats["avg_tokens"] == 20
    assert stats["max_tokens"] == 30
