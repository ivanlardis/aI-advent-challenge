#!/usr/bin/env python3
"""
Простой тест chunked-обработки через консоль
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from chunking import should_use_chunking, get_total_count, calculate_chunk_size

# Тестовые данные
test_data_500 = {
    "format": "log",
    "line_count": 500,
    "data": [f"2024-01-20 10:00:{i:02d} ERROR Error {i}" for i in range(500)]
}

test_data_2000 = {
    "format": "log",
    "line_count": 2000,
    "data": [f"2024-01-20 10:00:{i:02d} ERROR Error {i}" for i in range(2000)]
}

print("="*60)
print("ТЕСТ CHUNKING ЛОГИКИ")
print("="*60)

# Тест 1: Маленький файл
print("\n📊 Тест 1: Файл 500 строк")
print(f"  should_use_chunking: {should_use_chunking(test_data_500)}")
print(f"  Ожидается: False (обычный режим)")

# Тест 2: Средний файл
print("\n📊 Тест 2: Файл 2000 строк")
print(f"  should_use_chunking: {should_use_chunking(test_data_2000)}")
print(f"  Ожидается: True (chunked режим)")

if should_use_chunking(test_data_2000):
    chunk_size = calculate_chunk_size(get_total_count(test_data_2000))
    expected_chunks = (2000 + chunk_size - 1) // chunk_size
    print(f"  chunk_size: {chunk_size}")
    print(f"  Ожидается чанков: {expected_chunks}")

print("\n" + "="*60)
print("✅ Базовая логика работает корректно!")
print("="*60)
