#!/usr/bin/env python3
"""
Модуль chunked-обработки больших файлов через LLM
"""

import json
import math
from typing import Dict, List, Any


# ========================== КОНФИГУРАЦИЯ ==========================

BASE_CHUNK_SIZE = 500  # Базовый размер чанка в строках
LARGE_FILE_THRESHOLD = 50_000  # Порог для увеличения размера чанка
LARGE_CHUNK_SIZE = 1000  # Размер чанка для больших файлов
MAX_CHUNKS = 100  # Максимальное количество чанков
CHUNKING_THRESHOLD = 1000  # Минимальный размер для активации chunking


# ========================== ОПРЕДЕЛЕНИЕ СТРАТЕГИИ ==========================

def should_use_chunking(file_data: Dict) -> bool:
    """Определяет нужна ли chunked-обработка"""
    line_count = file_data.get("line_count", 0)
    row_count = file_data.get("row_count", 0)  # Для CSV
    count = file_data.get("count", 0)  # Для JSON array

    total = max(line_count, row_count, count)
    return total > CHUNKING_THRESHOLD


def calculate_chunk_size(total_lines: int) -> int:
    """Адаптивный размер чанка"""
    if total_lines > LARGE_FILE_THRESHOLD:
        return LARGE_CHUNK_SIZE
    return BASE_CHUNK_SIZE


# ========================== CHUNKING ПО ФОРМАТАМ ==========================

def chunk_log(file_data: Dict, chunk_size: int) -> List[Dict]:
    """Разбивает лог-файл на чанки"""
    lines = file_data["data"]
    chunks = []

    for i in range(0, len(lines), chunk_size):
        chunk = {
            "chunk_id": len(chunks),
            "format": "log",
            "data": lines[i:i + chunk_size],
            "line_count": len(lines[i:i + chunk_size])
        }
        chunks.append(chunk)

    return chunks


def chunk_csv(file_data: Dict, chunk_size: int) -> List[Dict]:
    """Разбивает CSV на чанки, добавляя header в каждый"""
    rows = file_data["data"]
    columns = file_data["columns"]
    chunks = []

    for i in range(0, len(rows), chunk_size):
        chunk = {
            "chunk_id": len(chunks),
            "format": "csv",
            "columns": columns,  # Header для каждого чанка
            "data": rows[i:i + chunk_size],
            "row_count": len(rows[i:i + chunk_size])
        }
        chunks.append(chunk)

    return chunks


def chunk_json(file_data: Dict, chunk_size: int) -> List[Dict]:
    """Разбивает JSON на чанки по top-level элементам"""
    data_type = file_data.get("type", "")
    chunks = []

    if data_type == "array":
        # Массив: режем по элементам
        array_data = file_data["data"]
        for i in range(0, len(array_data), chunk_size):
            chunk = {
                "chunk_id": len(chunks),
                "format": "json",
                "type": "array",
                "data": array_data[i:i + chunk_size],
                "count": len(array_data[i:i + chunk_size])
            }
            chunks.append(chunk)

    elif data_type == "object":
        # Объект: режем по ключам
        obj_data = file_data["data"]
        keys = list(obj_data.keys())

        for i in range(0, len(keys), chunk_size):
            chunk_keys = keys[i:i + chunk_size]
            chunk = {
                "chunk_id": len(chunks),
                "format": "json",
                "type": "object",
                "data": {k: obj_data[k] for k in chunk_keys},
                "keys": chunk_keys
            }
            chunks.append(chunk)

    else:
        # Примитив: возвращаем как есть
        chunks.append({
            "chunk_id": 0,
            "format": "json",
            "type": "primitive",
            "data": file_data["data"]
        })

    return chunks


def chunk_data(file_data: Dict, chunk_size: int) -> List[Dict]:
    """
    Разбивает данные на чанки с учётом формата.
    Применяет лимит на максимальное количество чанков.
    """
    fmt = file_data["format"]

    # Разбиваем по формату
    if fmt == "csv":
        chunks = chunk_csv(file_data, chunk_size)
    elif fmt == "json":
        chunks = chunk_json(file_data, chunk_size)
    elif fmt == "log":
        chunks = chunk_log(file_data, chunk_size)
    else:
        raise ValueError(f"Неподдерживаемый формат: {fmt}")

    # Применяем лимит на количество чанков
    if len(chunks) > MAX_CHUNKS:
        chunks = chunks[:MAX_CHUNKS]

    return chunks


# ========================== ПРОМПТ ИНЖИНИРИНГ ==========================

def build_chunk_prompt(chunk: Dict, question: str, chunk_num: int, total_chunks: int) -> str:
    """
    Создаёт промпт для обработки одного чанка.
    Использует few-shot примеры и строгий формат JSON.
    """

    # Few-shot пример для маленькой модели
    few_shot_example = """
ПРИМЕР:
Вопрос: Сколько ошибок ERROR?
Данные:
2024-01-20 10:00:00 INFO Application started
2024-01-20 10:05:00 ERROR Failed to connect
2024-01-20 10:10:00 ERROR Timeout
Ответ: {"count": 2, "items": [], "summary": "Найдено 2 записи ERROR"}
"""

    # Формируем данные для промпта
    chunk_content = format_chunk_for_prompt(chunk)

    system_prompt = """Ты — аналитик данных. Проанализируй ТОЛЬКО этот фрагмент данных.

ВАЖНО: Верни ответ СТРОГО в формате JSON без дополнительного текста:
{
  "count": <число>,
  "items": [<элементы, если нужны>],
  "summary": "<краткое описание>"
}
"""

    prompt = f"""{system_prompt}

{few_shot_example}

ДАННЫЕ (часть {chunk_num + 1}/{total_chunks}):
{chunk_content}

ВОПРОС:
{question}

Верни ТОЛЬКО JSON, ничего больше.
"""

    return prompt


def format_chunk_for_prompt(chunk: Dict) -> str:
    """Форматирует чанк в читаемый вид для промпта"""
    fmt = chunk["format"]

    if fmt == "log":
        # Лог: простой текст построчно
        return "\n".join(chunk["data"][:100])  # Лимит 100 строк для контекста

    elif fmt == "csv":
        # CSV: заголовок + строки
        result = "Колонки: " + ", ".join(chunk["columns"]) + "\n\n"
        for row in chunk["data"][:50]:  # Лимит 50 строк
            result += str(row) + "\n"
        return result

    elif fmt == "json":
        # JSON: форматированный JSON
        return json.dumps(chunk["data"], ensure_ascii=False, indent=2)[:3000]  # Лимит 3K символов

    return str(chunk["data"])


def make_stricter_prompt(original_prompt: str) -> str:
    """Создаёт более строгий промпт для retry"""
    return original_prompt.replace(
        "Верни ТОЛЬКО JSON, ничего больше.",
        "КРИТИЧЕСКИ ВАЖНО: Верни ИСКЛЮЧИТЕЛЬНО валидный JSON объект. Никакого текста до или после JSON. Только JSON."
    )


# ========================== АГРЕГАЦИЯ ==========================

def aggregate_simple(chunk_results: List[Dict]) -> Dict:
    """
    Простая агрегация в коде (для метрик типа count).
    Суммирует count и объединяет items.
    """
    total_count = sum(r.get("count", 0) for r in chunk_results)
    all_items = []
    all_summaries = []

    for result in chunk_results:
        items = result.get("items", [])
        if items:
            all_items.extend(items)

        summary = result.get("summary", "")
        if summary:
            all_summaries.append(summary)

    return {
        "total_count": total_count,
        "all_items": all_items,
        "summaries": all_summaries
    }


def build_aggregation_prompt(chunk_results: List[Dict], question: str) -> str:
    """Создаёт промпт для финальной агрегации через LLM"""

    # Двухуровневая агрегация: группируем по 10
    if len(chunk_results) > 10:
        return build_two_level_aggregation_prompt(chunk_results, question)

    # Простая агрегация для ≤10 чанков
    summaries = []
    for i, result in enumerate(chunk_results):
        summaries.append(f"Часть {i + 1}: {result.get('summary', str(result))}")

    summaries_text = "\n".join(summaries)

    prompt = f"""На основе результатов анализа {len(chunk_results)} частей данных дай общий ответ.

РЕЗУЛЬТАТЫ ПО ЧАСТЯМ:
{summaries_text}

ИСХОДНЫЙ ВОПРОС:
{question}

Дай итоговый ответ, объединив информацию из всех частей.
"""

    return prompt


def build_two_level_aggregation_prompt(chunk_results: List[Dict], question: str) -> str:
    """Двухуровневая агрегация для >10 чанков"""

    # Группируем результаты по 10
    groups = [chunk_results[i:i + 10] for i in range(0, len(chunk_results), 10)]

    # Для каждой группы создаём краткое summary
    group_summaries = []
    for g_idx, group in enumerate(groups):
        total_count = sum(r.get("count", 0) for r in group)
        group_summaries.append(
            f"Группа {g_idx + 1} (части {g_idx * 10 + 1}-{min((g_idx + 1) * 10, len(chunk_results))}): count={total_count}"
        )

    summaries_text = "\n".join(group_summaries)

    prompt = f"""Объедини результаты из {len(groups)} групп данных.

РЕЗУЛЬТАТЫ ПО ГРУППАМ:
{summaries_text}

ИСХОДНЫЙ ВОПРОС:
{question}

Дай итоговый ответ.
"""

    return prompt


# ========================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========================

def get_total_count(file_data: Dict) -> int:
    """Получает общее количество строк/записей из file_data"""
    return max(
        file_data.get("line_count", 0),
        file_data.get("row_count", 0),
        file_data.get("count", 0)
    )


def extract_number_from_text(text: str) -> int:
    """
    Пытается извлечь число из текста (fallback для нестабильных LLM ответов).
    Ищет первое число в тексте.
    """
    import re
    match = re.search(r'\d+', text)
    if match:
        return int(match.group())
    return 0
