#!/usr/bin/env python3
"""
Тест для проверки chunking логики
"""

import chunking
import json

# Тест 1: Определение необходимости chunking
print("=" * 60)
print("ТЕСТ 1: Определение необходимости chunking")
print("=" * 60)

small_data = {"line_count": 500, "format": "log"}
large_data = {"line_count": 5000, "format": "log"}

print(f"Файл 500 строк: chunking = {chunking.should_use_chunking(small_data)}")
print(f"Файл 5000 строк: chunking = {chunking.should_use_chunking(large_data)}")

# Тест 2: Размер чанка
print("\n" + "=" * 60)
print("ТЕСТ 2: Вычисление размера чанка")
print("=" * 60)

print(f"10K строк: chunk_size = {chunking.calculate_chunk_size(10000)}")
print(f"60K строк: chunk_size = {chunking.calculate_chunk_size(60000)}")

# Тест 3: Разбиение лог-файла
print("\n" + "=" * 60)
print("ТЕСТ 3: Разбиение лог-файла на чанки")
print("=" * 60)

log_data = {
    "format": "log",
    "line_count": 2500,
    "data": [f"2024-01-20 10:00:{i:02d} INFO Log line {i}" for i in range(2500)]
}

chunks = chunking.chunk_log(log_data, 500)
print(f"Всего строк: {log_data['line_count']}")
print(f"Размер чанка: 500")
print(f"Создано чанков: {len(chunks)}")
print(f"Первый чанк: {chunks[0]['line_count']} строк")
print(f"Последний чанк: {chunks[-1]['line_count']} строк")

# Тест 4: Разбиение CSV
print("\n" + "=" * 60)
print("ТЕСТ 4: Разбиение CSV на чанки")
print("=" * 60)

csv_data = {
    "format": "csv",
    "columns": ["id", "name", "value"],
    "row_count": 1200,
    "data": [{"id": i, "name": f"Item{i}", "value": i * 10} for i in range(1200)]
}

csv_chunks = chunking.chunk_csv(csv_data, 500)
print(f"Всего строк: {csv_data['row_count']}")
print(f"Размер чанка: 500")
print(f"Создано чанков: {len(csv_chunks)}")
print(f"Каждый чанк содержит header: {csv_chunks[0]['columns']}")
print(f"Первый чанк: {csv_chunks[0]['row_count']} строк")

# Тест 5: Построение промпта для чанка
print("\n" + "=" * 60)
print("ТЕСТ 5: Построение промпта для чанка")
print("=" * 60)

test_chunk = {
    "format": "log",
    "data": [
        "2024-01-20 10:00:00 INFO Started",
        "2024-01-20 10:00:05 ERROR Connection failed",
        "2024-01-20 10:00:10 ERROR Timeout"
    ]
}

prompt = chunking.build_chunk_prompt(test_chunk, "Сколько ошибок ERROR?", 0, 5)
print("Промпт для чанка 1/5:")
print("-" * 60)
print(prompt[:500] + "...")  # Показываем начало промпта

# Тест 6: Агрегация результатов
print("\n" + "=" * 60)
print("ТЕСТ 6: Агрегация результатов")
print("=" * 60)

chunk_results = [
    {"count": 5, "items": [], "summary": "Чанк 1: 5 ошибок"},
    {"count": 3, "items": [], "summary": "Чанк 2: 3 ошибки"},
    {"count": 7, "items": [], "summary": "Чанк 3: 7 ошибок"},
]

aggregated = chunking.aggregate_simple(chunk_results)
print(f"Результаты 3 чанков:")
for r in chunk_results:
    print(f"  - {r['summary']}")
print(f"\nОбщее количество: {aggregated['total_count']}")

# Тест 7: Двухуровневая агрегация
print("\n" + "=" * 60)
print("ТЕСТ 7: Двухуровневая агрегация (>10 чанков)")
print("=" * 60)

many_results = [
    {"count": i, "summary": f"Чанк {i}: {i} элементов"}
    for i in range(1, 25)  # 24 чанка
]

agg_prompt = chunking.build_aggregation_prompt(many_results, "Сколько всего элементов?")
print(f"Чанков: {len(many_results)}")
print("Промпт двухуровневой агрегации:")
print("-" * 60)
print(agg_prompt[:400] + "...")

print("\n" + "=" * 60)
print("ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
print("=" * 60)
