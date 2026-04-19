"""Тесты для lib/profile."""

from pathlib import Path

from lib.profile import (
    load_profile,
    extract_name,
    list_sections,
    get_profile_summary,
    truncate_preview,
)


def test_load_profile_missing_returns_empty(tmp_path):
    assert load_profile("nope.md", base_dir=tmp_path) == ""


def test_load_profile_reads_file(tmp_path):
    profile_file = tmp_path / "config" / "profile.md"
    profile_file.parent.mkdir()
    profile_file.write_text("hello", encoding="utf-8")
    assert load_profile("config/profile.md", base_dir=tmp_path) == "hello"


def test_extract_name_from_profile():
    content = "# Profile\n- **Имя:** Иван\n- **Возраст:** 32"
    assert extract_name(content) == "Иван"


def test_extract_name_fallback_when_missing():
    assert extract_name("no name here") == "Пользователь"


def test_extract_name_empty_input():
    assert extract_name("") == "Пользователь"


def test_extract_name_empty_value():
    assert extract_name("- **Имя:** \n") == "Пользователь"


def test_extract_name_empty_profile_acceptance():
    """Явный acceptance-тест T-15: пустой профиль → 'Пользователь'."""
    assert extract_name("") == "Пользователь"


def test_extract_name_whitespace_only_value():
    """Значение из одних пробелов/табов также даёт fallback."""
    assert extract_name("- **Имя:**     \t  \n") == "Пользователь"


def test_list_sections_empty():
    assert list_sections("") == []


def test_list_sections_finds_h2():
    content = "# Top\n## One\n text\n## Two\n### Nested"
    assert list_sections(content) == ["One", "Two"]


def test_get_profile_summary_empty():
    out = get_profile_summary("")
    assert "не загружен" in out.lower()


def test_truncate_preview_short_text_no_suffix():
    assert truncate_preview("abc", 200) == "abc"


def test_truncate_preview_long_text_gets_ellipsis():
    assert truncate_preview("a" * 250, 200) == "a" * 200 + "..."


def test_truncate_preview_exact_limit_no_suffix():
    assert truncate_preview("a" * 200, 200) == "a" * 200


def test_get_profile_summary_has_name_and_sections():
    content = "- **Имя:** Иван\n## Цели\n## Интересы"
    out = get_profile_summary(content)
    assert "Иван" in out
    assert "Цели" in out
    assert "Интересы" in out
    assert "2" in out
