"""RAG сервис для God Agent."""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np


class SimpleRAG:
    """Простой RAG сервис с FAISS."""

    def __init__(
        self,
        data_file: str = "data/rag_example_cities_ru.txt",
        index_dir: str = "data/faiss_index",
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"
    ):
        self.data_file = data_file
        self.index_dir = index_dir
        self.model_name = model_name
        self.documents: List[Dict[str, Any]] = []
        self.embeddings = None
        self.index = None
        self._initialized = False

    async def initialize(self):
        """Инициализирует RAG индекс."""
        if self._initialized:
            return

        try:
            from sentence_transformers import SentenceTransformer
            import faiss

            # Загружаем модель
            self.model = SentenceTransformer(self.model_name)

            # Загружаем документы
            self._load_documents()

            if not self.documents:
                print("RAG: Нет документов для индексации")
                return

            # Создаём embeddings
            texts = [doc["text"] for doc in self.documents]
            self.embeddings = self.model.encode(texts, convert_to_numpy=True)

            # Создаём FAISS индекс
            dimension = self.embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dimension)
            faiss.normalize_L2(self.embeddings)
            self.index.add(self.embeddings)

            self._initialized = True
            print(f"RAG: Загружено {len(self.documents)} документов")

        except ImportError as e:
            print(f"RAG: Ошибка импорта - {e}")
            print("Установите: pip install faiss-cpu sentence-transformers")

    def _load_documents(self):
        """Загружает документы из файла."""
        data_path = Path(self.data_file)

        if not data_path.exists():
            print(f"RAG: Файл {data_path} не найден")
            return

        with open(data_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Парсим документы (формат: Город: описание)
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if ":" in line:
                parts = line.split(":", 1)
                city = parts[0].strip()
                text = parts[1].strip() if len(parts) > 1 else ""
            else:
                city = "Общее"
                text = line

            self.documents.append({
                "city": city,
                "text": text,
                "source": self.data_file
            })

    async def search(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Ищет релевантные документы."""
        if not self._initialized or self.index is None:
            return []

        try:
            import faiss

            # Создаём embedding для запроса
            query_embedding = self.model.encode([query], convert_to_numpy=True)
            faiss.normalize_L2(query_embedding)

            # Поиск
            scores, indices = self.index.search(query_embedding, top_k)

            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or score < min_score:
                    continue

                doc = self.documents[idx].copy()
                doc["score"] = float(score)
                results.append(doc)

            return results

        except Exception as e:
            print(f"RAG search error: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику индекса."""
        return {
            "total_documents": len(self.documents),
            "initialized": self._initialized,
            "model": self.model_name
        }


def format_rag_context(results: List[Dict[str, Any]]) -> str:
    """Форматирует результаты RAG для промпта."""
    if not results:
        return ""

    parts = ["Найденная информация из базы знаний:\n"]
    for i, result in enumerate(results, 1):
        city = result.get("city", "")
        text = result.get("text", "")
        score = result.get("score", 0.0)
        parts.append(f"{i}. {city}: {text} (релевантность: {score:.2f})")

    return "\n".join(parts)


def format_sources(results: List[Dict[str, Any]]) -> str:
    """Форматирует источники для вывода."""
    if not results:
        return ""

    lines = ["\n\n---\n**Источники:**"]
    for i, result in enumerate(results, 1):
        city = result.get("city", "")
        score = result.get("score", 0.0)
        lines.append(f"{i}. {city} (релевантность: {score:.2f})")

    return "\n".join(lines)
