"""Тесты для lib/profile."""

from pathlib import Path

from lib.profile import (
    load_profile,
    extract_name,
    list_sections,
    get_profile_summary,
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


def test_list_sections_empty():
    assert list_sections("") == []


def test_list_sections_finds_h2():
    content = "# Top\n## One\n text\n## Two\n### Nested"
    assert list_sections(content) == ["One", "Two"]


def test_get_profile_summary_empty():
    out = get_profile_summary("")
    assert "не загружен" in out.lower()


def test_get_profile_summary_has_name_and_sections():
    content = "- **Имя:** Иван\n## Цели\n## Интересы"
    out = get_profile_summary(content)
    assert "Иван" in out
    assert "Цели" in out
    assert "Интересы" in out
    assert "2" in out
