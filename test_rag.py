"""Тестовый скрипт для проверки RAG-пайплайна."""

import asyncio
import logging

from app.rag.rag_service import CityRAG

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Тестирование RAG-пайплайна."""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ RAG-ПАЙПЛАЙНА")
    print("=" * 60)

    # Инициализация RAG
    print("\n1. Инициализация CityRAG...")
    rag = CityRAG(
        data_file="rag_example_cities_ru.txt",
        index_dir="data/faiss_index",
        model_name="intfloat/multilingual-e5-large",
        deduplicate=True
    )

    print("\n2. Загрузка или создание индекса...")
    await rag.initialize()

    # Статистика
    print("\n3. Статистика индекса:")
    stats = rag.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Тестовые запросы
    test_queries = [
        "Расскажи про город Москва",
        "В каком федеральном округе находится Екатеринбург?",
        "Какие города есть в Южном федеральном округе?",
        "Что ты знаешь про Санкт-Петербург?",
    ]

    print("\n4. Тестовые запросы:")
    for i, query in enumerate(test_queries, 1):
        print(f"\n   Запрос {i}: {query}")
        results = rag.search(query, k=3)

        if results:
            print(f"   Найдено {len(results)} результатов:")
            for j, result in enumerate(results, 1):
                city = result.get("city", "?")
                score = result.get("score", 0.0)
                text_preview = result.get("text", "")[:100]
                print(f"      {j}. {city} (score: {score:.3f})")
                print(f"         {text_preview}...")
        else:
            print("   Результаты не найдены.")

    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
