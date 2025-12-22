"""Модуль для парсинга файла городов России."""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def parse_cities_file(file_path: str) -> List[Dict[str, str]]:
    """
    Парсит файл справочника городов России.

    Формат входного файла:
        Город: Название
        Описание города в один абзац...

        Город: Другое название
        Описание другого города...

    Args:
        file_path: Путь к файлу с данными о городах

    Returns:
        Список документов в формате:
        [
            {
                "city": "Название города",
                "text": "Полный текст описания",
                "source": "путь к файлу"
            },
            ...
        ]
    """
    documents = []
    current_city = None
    current_text = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                if line.startswith("Город:"):
                    # Сохраняем предыдущий город
                    if current_city and current_text:
                        documents.append({
                            "city": current_city,
                            "text": " ".join(current_text),
                            "source": file_path
                        })

                    # Начинаем новый город
                    current_city = line.replace("Город:", "").strip()
                    current_text = []

                elif line:
                    # Добавляем текст к текущему городу
                    current_text.append(line)

            # Сохраняем последний город
            if current_city and current_text:
                documents.append({
                    "city": current_city,
                    "text": " ".join(current_text),
                    "source": file_path
                })

        logger.info(f"Спарсено {len(documents)} документов из {file_path}")
        return documents

    except FileNotFoundError:
        logger.error(f"Файл не найден: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Ошибка парсинга файла {file_path}: {e}")
        raise


def deduplicate_cities(documents: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Объединяет дубликаты городов.

    Если город встречается несколько раз, объединяет информацию
    из всех упоминаний в один документ.

    Args:
        documents: Список документов с возможными дубликатами

    Returns:
        Список уникальных документов
    """
    city_map = {}

    for doc in documents:
        city = doc["city"]
        if city not in city_map:
            city_map[city] = doc.copy()
        else:
            # Объединяем тексты, избегая полных дубликатов
            existing_text = city_map[city]["text"]
            new_text = doc["text"]

            if new_text not in existing_text:
                city_map[city]["text"] = f"{existing_text} {new_text}"

    unique_docs = list(city_map.values())
    logger.info(f"Дедупликация: {len(documents)} -> {len(unique_docs)} документов")

    return unique_docs
