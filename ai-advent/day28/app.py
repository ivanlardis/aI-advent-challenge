#!/usr/bin/env python3
"""
Локальный аналитик данных
Анализ CSV, JSON и логов с помощью локальной LLM через Ollama
"""

import asyncio
import csv
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

import chainlit as cl
import requests

# Chunked-обработка
import chunking


# ========================== КОНФИГУРАЦИЯ ==========================

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:0.5b"  # Возвращаемся на qwen
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


# ========================== OLLAMA UTILS ==========================

def check_ollama_health() -> bool:
    """Проверяет доступность Ollama"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def try_start_ollama() -> bool:
    """Пытается запустить Ollama в фоне"""
    try:
        subprocess.Popen(
            ['ollama', 'serve'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(3)  # Даём время на запуск
        return check_ollama_health()
    except Exception:
        return False


def ensure_ollama_running() -> str:
    """
    Проверяет что Ollama запущена, пытается запустить если нет.
    Возвращает сообщение о статусе.
    """
    if check_ollama_health():
        return "✅ Ollama доступна"

    # Пытаемся запустить
    if try_start_ollama():
        return "✅ Ollama запущена автоматически"

    # Не удалось
    return """
❌ Ollama недоступна!

Пожалуйста, запустите Ollama вручную:
```bash
ollama serve
```

Затем перезагрузите страницу.
"""


def call_ollama(prompt: str) -> str:
    """Отправляет запрос к Ollama и возвращает ответ"""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            return result.get("response", "Не удалось получить ответ")
        else:
            return f"Ошибка Ollama API: {response.status_code}"

    except requests.exceptions.Timeout:
        return "⏱️ Запрос превысил время ожидания (60 сек)"
    except Exception as e:
        return f"❌ Ошибка при обращении к Ollama: {str(e)}"


# ========================== CHUNKED-ОБРАБОТКА ==========================

async def process_chunk(chunk: Dict, question: str, chunk_num: int, total_chunks: int) -> Dict:
    """
    Обрабатывает один чанк через LLM с retry логикой.
    Возвращает структурированный результат в формате JSON.
    """
    max_retries = 2
    prompt = chunking.build_chunk_prompt(chunk, question, chunk_num, total_chunks)

    # Отладка
    print(f"\n🔍 Чанк {chunk_num+1}/{total_chunks}:")
    print(f"📦 Вопрос: {question}")
    print(f"📊 Данных в чанке: {len(chunk.get('data', []))} строк/элементов")
    print(f"📝 Длина промпта: {len(prompt)} символов")

    for attempt in range(max_retries):
        print(f"  → Попытка {attempt+1}/{max_retries}")
        response = call_ollama(prompt)
        print(f"  ← Ответ: {response[:100]}...")  # Первые 100 символов

        # Пытаемся распарсить JSON
        try:
            # Ищем JSON в ответе (может быть обёрнут в текст)
            response = response.strip()

            # Если начинается с ```json, извлекаем
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            response = response.strip()

            result = json.loads(response)

            # Проверяем наличие обязательных полей
            if "count" not in result:
                result["count"] = 0
            if "items" not in result:
                result["items"] = []
            if "summary" not in result:
                result["summary"] = ""

            return result

        except json.JSONDecodeError:
            if attempt < max_retries - 1:
                # Retry с более строгим промптом
                prompt = chunking.make_stricter_prompt(prompt)
            else:
                # Финальная попытка: извлечь число из текста
                count = chunking.extract_number_from_text(response)
                return {
                    "count": count,
                    "items": [],
                    "summary": response[:200]  # Обрезаем длинный ответ
                }

    # Fallback (не должно дойти сюда)
    return {"count": 0, "items": [], "summary": "Ошибка обработки чанка"}


async def process_chunked(data: Dict, question: str) -> str:
    """
    Полная chunked-обработка файла с прогресс-баром.
    Возвращает финальный ответ пользователю.
    """
    import logging
    logger = logging.getLogger(__name__)

    # Вычисляем размер чанка и создаём чанки
    total_count = chunking.get_total_count(data)
    chunk_size = chunking.calculate_chunk_size(total_count)
    chunks = chunking.chunk_data(data, chunk_size)

    # Информируем пользователя о chunked-режиме
    info_msg = f"📊 Файл большой ({total_count} строк). Обработка по частям: {len(chunks)} чанков по {chunk_size} строк."
    await cl.Message(content=info_msg).send()

    # Прогресс-бар
    progress_msg = await cl.Message(
        content=f"🔄 Обработка 0/{len(chunks)} (0%)"
    ).send()

    # Обрабатываем чанки
    chunk_results = []
    import time as time_module
    start_time = time_module.time()

    for i, chunk in enumerate(chunks):
        chunk_start = time_module.time()
        result = await process_chunk(chunk, question, i, len(chunks))
        chunk_elapsed = time_module.time() - chunk_start

        chunk_results.append(result)

        # Логируем время
        logger.info(f"Chunk {i+1}/{len(chunks)} processed in {chunk_elapsed:.2f}s")
        print(f"⏱️ Чанк {i+1}/{len(chunks)}: {chunk_elapsed:.2f} сек")

        # Обновляем прогресс
        percent = int((i + 1) / len(chunks) * 100)
        progress_msg.content = f"🔄 Обработано {i + 1}/{len(chunks)} ({percent}%) | Последний чанк: {chunk_elapsed:.1f}s"
        await progress_msg.update()

    total_elapsed = time_module.time() - start_time
    logger.info(f"Total processing time: {total_elapsed:.2f}s")
    print(f"⏱️ ВСЕГО: {total_elapsed:.2f} сек")

    # Финальная агрегация
    progress_msg.content = "✨ Формирую итоговый ответ..."
    await progress_msg.update()

    # Проверяем можно ли агрегировать в коде (простые метрики)
    if is_simple_aggregation(question):
        # Простая агрегация: сумма в коде
        aggregated = chunking.aggregate_simple(chunk_results)
        total = aggregated["total_count"]
        items = aggregated["all_items"]

        # Формируем финальный ответ через LLM
        final_prompt = f"""На основе анализа {len(chunks)} частей данных:

Общее количество: {total}
{f'Найдено элементов: {len(items)}' if items else ''}

Вопрос был: {question}

Дай итоговый ответ пользователю на русском языке.
"""
        answer = call_ollama(final_prompt)

    else:
        # Сложная агрегация: через LLM
        aggregation_prompt = chunking.build_aggregation_prompt(chunk_results, question)
        answer = call_ollama(aggregation_prompt)

    await progress_msg.remove()
    return answer


def is_simple_aggregation(question: str) -> bool:
    """Определяет можно ли использовать простую агрегацию (сумма в коде)"""
    simple_keywords = ["сколько", "количество", "count", "число", "всего"]
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in simple_keywords)


# ========================== ПАРСЕРЫ ДАННЫХ ==========================

def parse_csv(file_path: str) -> Dict[str, Any]:
    """
    Парсит CSV файл в структурированный JSON.
    Автоопределяет разделитель, пропускает невалидные строки.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Читаем первые строки для определения разделителя
            sample = f.read(1024)
            f.seek(0)

            # Определяем разделитель
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter

            # Читаем CSV
            reader = csv.DictReader(f, delimiter=delimiter)
            rows = []
            skipped = 0

            for i, row in enumerate(reader):
                try:
                    # Пропускаем строки с пустыми значениями для всех полей
                    if all(v.strip() == '' for v in row.values()):
                        skipped += 1
                        continue
                    rows.append(row)
                except Exception:
                    skipped += 1

            return {
                "format": "csv",
                "columns": list(rows[0].keys()) if rows else [],
                "row_count": len(rows),
                "skipped_rows": skipped,
                "data": rows
            }

    except Exception as e:
        raise ValueError(f"Ошибка при парсинге CSV: {str(e)}")


def parse_json(file_path: str) -> Dict[str, Any]:
    """Парсит JSON файл"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

            # Определяем тип JSON (массив или объект)
            if isinstance(data, list):
                return {
                    "format": "json",
                    "type": "array",
                    "count": len(data),
                    "data": data
                }
            elif isinstance(data, dict):
                return {
                    "format": "json",
                    "type": "object",
                    "keys": list(data.keys()),
                    "data": data
                }
            else:
                return {
                    "format": "json",
                    "type": "primitive",
                    "data": data
                }

    except json.JSONDecodeError as e:
        raise ValueError(f"Невалидный JSON: {str(e)}")
    except Exception as e:
        raise ValueError(f"Ошибка при парсинге JSON: {str(e)}")


def parse_log(file_path: str) -> Dict[str, Any]:
    """Парсит текстовый лог-файл (без семплирования - chunking обрабатывает всё)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = []

            for line in f:
                line = line.strip()
                if line:  # Пропускаем пустые строки
                    lines.append(line)

            return {
                "format": "log",
                "line_count": len(lines),
                "data": lines
            }

    except Exception as e:
        raise ValueError(f"Ошибка при парсинге LOG: {str(e)}")


def parse_file(file_path: str) -> Dict[str, Any]:
    """
    Автоопределяет формат файла и парсит его.
    Возвращает структурированный JSON.
    """
    extension = Path(file_path).suffix.lower()

    if extension == '.csv':
        return parse_csv(file_path)
    elif extension == '.json':
        return parse_json(file_path)
    elif extension in ['.log', '.txt']:
        return parse_log(file_path)
    else:
        raise ValueError(f"Неподдерживаемый формат файла: {extension}")


# ========================== ПРОМПТ ИНЖИНИРИНГ ==========================

def build_analysis_prompt(data: Dict[str, Any], question: str) -> str:
    """Создаёт структурированный промпт для LLM"""

    fmt = data.get("format", "")

    # Упрощаем представление данных для маленькой модели
    if fmt == "csv":
        # Для CSV - простое табличное представление
        data_text = "Колонки: " + ", ".join(data["columns"]) + "\n\n"
        data_text += "Данные:\n"
        for row in data["data"]:
            data_text += str(row) + "\n"

    elif fmt == "json":
        data_type = data.get("type", "")
        if data_type == "array":
            data_text = f"Массив из {data['count']} элементов:\n"
            for i, item in enumerate(data["data"][:50]):  # Ограничиваем для контекста
                data_text += f"{i+1}. {json.dumps(item, ensure_ascii=False)}\n"
        else:
            data_text = json.dumps(data["data"], ensure_ascii=False, indent=2)

    elif fmt == "log":
        data_text = f"Лог-файл ({data['line_count']} строк):\n\n"

        # Ограничиваем вывод для обычного режима (без chunking)
        for line in data["data"][:200]:  # Первые 200 строк для контекста
            data_text += line + "\n"
    else:
        data_text = json.dumps(data, ensure_ascii=False, indent=2)

    system_prompt = ""

    data_section = f"ЛОГ:\n{data_text}"

    instruction = f"""ВОПРОС: {question}

ОТВЕТЬ ПО-РУССКИ КРАТКО:"""

    question_section = ""

    return f"{system_prompt}\n\n{data_section}\n\n{instruction}\n\n{question_section}"


# ========================== АДАПТИВНЫЕ ПРИМЕРЫ ==========================

def get_suggested_questions(data_format: str) -> List[str]:
    """Возвращает примеры вопросов в зависимости от формата данных"""

    suggestions = {
        "csv": [
            "Сколько всего записей в файле?",
            "Какие уникальные значения в каждой колонке?",
            "Покажи статистику по числовым полям",
            "Есть ли дубликаты?"
        ],
        "json": [
            "Какая структура данных?",
            "Сколько объектов на верхнем уровне?",
            "Какие поля присутствуют во всех записях?",
            "Покажи сводку по данным"
        ],
        "log": [
            "Какая ошибка встречается чаще всего?",
            "Сколько записей уровня ERROR/WARN/INFO?",
            "В какое время произошло больше всего ошибок?",
            "Какие основные события в логе?"
        ]
    }

    return suggestions.get(data_format, [])


# ========================== CHAINLIT HANDLERS ==========================

@cl.on_chat_start
async def start():
    """Инициализация чата"""

    # Проверяем Ollama
    status = ensure_ollama_running()

    welcome_msg = f"""# 🔍 Локальный аналитик данных

{status}

Загрузите файл (CSV, JSON или LOG) для начала анализа.

**Возможности:**
- 📊 Поддержка больших файлов (автоматическая chunked-обработка для >1000 строк)
- 🔄 Прогресс-бар для длительных операций
- 🎯 Точная агрегация результатов из всех частей файла

**Ограничения:**
- Максимальный размер файла: {MAX_FILE_SIZE_MB}MB
- Поддерживаемые форматы: .csv, .json, .log, .txt
- Максимум обрабатываемых чанков: 100
"""

    await cl.Message(content=welcome_msg).send()

    # Инициализируем сессию
    cl.user_session.set("data", None)
    cl.user_session.set("data_format", None)


@cl.on_message
async def main(message: cl.Message):
    """Обработка сообщений пользователя"""

    # Отладка
    print(f"\n{'='*60}")
    print(f"🔔 Получено сообщение:")
    print(f"  Content: {message.content[:100] if message.content else 'None'}")
    print(f"  Elements: {len(message.elements) if message.elements else 0}")
    print(f"{'='*60}\n")

    # Обработка загруженных файлов
    if message.elements:
        print("📁 Обработка загруженного файла...")
        await handle_file_upload(message.elements)

        # Проверяем, есть ли текст вопроса вместе с файлом
        question = message.content.strip() if message.content else ""
        if question:
            print(f"❓ Есть вопрос вместе с файлом: {question}")
            # Даём файлу обработаться и ждём немного
            await asyncio.sleep(1)

            # Получаем данные
            data = cl.user_session.get("data")
            if data:
                # Обрабатываем вопрос
                if chunking.should_use_chunking(data):
                    print("🔄 Используется chunked-обработка")
                    answer = await process_chunked(data, question)
                    await cl.Message(content=answer).send()
                else:
                    print("📝 Используется обычная обработка")
                    prompt = build_analysis_prompt(data, question)
                    thinking_msg = await cl.Message(content="🤔 Анализирую данные...").send()
                    answer = call_ollama(prompt)
                    await thinking_msg.remove()
                    await cl.Message(content=answer).send()

        return

    # Проверяем, загружены ли данные
    data = cl.user_session.get("data")

    print(f"📊 Данные в сессии: {data is not None}")
    if data:
        print(f"  Формат: {data.get('format')}")
        print(f"  Строк: {data.get('line_count', data.get('row_count', data.get('count', 0)))}")

    if data is None:
        await cl.Message(
            content="❌ Сначала загрузите файл с данными для анализа."
        ).send()
        return

    # Обрабатываем вопрос пользователя
    question = message.content.strip()
    print(f"❓ Вопрос пользователя: {question}")

    if not question:
        await cl.Message(content="Пожалуйста, задайте вопрос о данных.").send()
        return

    # Выбираем стратегию обработки
    if chunking.should_use_chunking(data):
        print("🔄 Используется chunked-обработка")
        # Chunked-обработка для больших файлов
        answer = await process_chunked(data, question)
        await cl.Message(content=answer).send()

    else:
        print("📝 Используется обычная обработка")
        # Обычная обработка для небольших файлов
        prompt = build_analysis_prompt(data, question)
        print(f"📤 Длина промпта: {len(prompt)} символов")

        thinking_msg = await cl.Message(content="🤔 Анализирую данные...").send()
        answer = call_ollama(prompt)

        await thinking_msg.remove()
        await cl.Message(content=answer).send()


async def handle_file_upload(elements: List):
    """Обработка загруженного файла"""

    file_element = elements[0]  # Берём первый файл

    # Сбрасываем предыдущие данные (новый файл = новая сессия)
    previous_data = cl.user_session.get("data")
    if previous_data is not None:
        await cl.Message(
            content="📄 Загружен новый файл. История чата сброшена."
        ).send()

    # Очищаем сессию
    cl.user_session.set("data", None)
    cl.user_session.set("data_format", None)

    # Проверяем размер
    file_size = os.path.getsize(file_element.path)
    if file_size > MAX_FILE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        await cl.Message(
            content=f"❌ Файл слишком большой ({size_mb:.1f}MB). Максимум: {MAX_FILE_SIZE_MB}MB"
        ).send()
        return

    # Проверяем, что файл не пустой
    if file_size == 0:
        await cl.Message(
            content="❌ Файл пустой. Пожалуйста, загрузите файл с данными."
        ).send()
        return

    # Парсим файл
    try:
        data = parse_file(file_element.path)
        data_format = data["format"]

        # Сохраняем в сессию
        cl.user_session.set("data", data)
        cl.user_session.set("data_format", data_format)

        # Формируем сообщение о загрузке
        if data_format == "csv":
            info = f"**CSV файл загружен!**\n\n"
            info += f"- Колонок: {len(data['columns'])}\n"
            info += f"- Строк: {data['row_count']}\n"
            if data['skipped_rows'] > 0:
                info += f"- Пропущено невалидных строк: {data['skipped_rows']}\n"

        elif data_format == "json":
            info = f"**JSON файл загружен!**\n\n"
            if data['type'] == 'array':
                info += f"- Тип: массив\n"
                info += f"- Элементов: {data['count']}\n"
            elif data['type'] == 'object':
                info += f"- Тип: объект\n"
                info += f"- Ключей: {len(data['keys'])}\n"

        elif data_format == "log":
            info = f"**LOG файл загружен!**\n\n"
            info += f"- Строк: {data['line_count']}\n"

        # Информация о chunked-обработке
        if chunking.should_use_chunking(data):
            total_count = chunking.get_total_count(data)
            chunk_size = chunking.calculate_chunk_size(total_count)
            num_chunks = (total_count + chunk_size - 1) // chunk_size  # Округление вверх

            info += f"\n💡 **Режим обработки:** Chunked (файл большой)\n"
            info += f"- Будет обработано частями: ~{num_chunks} чанков по {chunk_size} строк\n"
        else:
            info += f"\n💡 **Режим обработки:** Обычный (одним запросом)\n"

        # Добавляем примеры вопросов
        suggestions = get_suggested_questions(data_format)
        if suggestions:
            info += f"\n**Примеры вопросов:**\n"
            for q in suggestions:
                info += f"- {q}\n"

        await cl.Message(content=info).send()

    except ValueError as e:
        await cl.Message(
            content=f"❌ Ошибка обработки файла:\n{str(e)}"
        ).send()
    except Exception as e:
        await cl.Message(
            content=f"❌ Неожиданная ошибка:\n{str(e)}"
        ).send()


# ========================== ENTRY POINT ==========================

if __name__ == "__main__":
    # Проверяем Ollama при запуске
    print("🔍 Проверка Ollama...")
    status = ensure_ollama_running()
    print(status)

    if "❌" not in status:
        print(f"\n✅ Приложение готово к запуску!")
        print(f"📊 Модель: {OLLAMA_MODEL}")
        print(f"🌐 Ollama URL: {OLLAMA_URL}")
