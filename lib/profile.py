"""Работа с профилем пользователя: загрузка, парсинг, саммари."""

import re
from pathlib import Path
from typing import List, Optional


def truncate_preview(text: str, limit: int = 200) -> str:
    """Обрезает текст до ``limit`` символов и добавляет ``...`` если был срез.

    Если длина ``text`` не превышает ``limit`` — возвращает исходную строку без суффикса.
    """
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def load_profile(profile_path: str = "config/profile.md", base_dir: Optional[Path] = None) -> str:
    """Загружает профиль пользователя из MD файла. Возвращает пустую строку если нет."""
    if base_dir is None:
        base_dir = Path(__file__).parent.parent
    full_path = base_dir / profile_path

    try:
        return full_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except Exception:
        return ""


def extract_name(profile_content: str) -> str:
    """Извлекает имя пользователя из профиля (строка `- **Имя:** <имя>`)."""
    if not profile_content:
        return "Пользователь"
    match = re.search(r"- \*\*Имя:\*\*\s*(.+)", profile_content)
    if match:
        name = match.group(1).strip()
        if name:
            return name
    return "Пользователь"


def list_sections(profile_content: str) -> List[str]:
    """Возвращает заголовки второго уровня (## ...) из профиля."""
    if not profile_content:
        return []
    return [line[3:].strip() for line in profile_content.splitlines() if line.startswith("## ")]


def get_profile_summary(profile_content: str) -> str:
    """Короткое саммари профиля для команды /profile."""
    if not profile_content:
        return "**Профиль не загружен.**"

    name = extract_name(profile_content)
    sections = list_sections(profile_content)

    lines = [
        f"**Профиль: {name}**",
        "",
        f"Загружено секций: `{len(sections)}`",
    ]

    if sections:
        lines.append("")
        lines.append("**Секции:**")
        for s in sections:
            lines.append(f"- {s}")

    return "\n".join(lines)
