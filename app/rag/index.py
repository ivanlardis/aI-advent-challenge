"""Модуль для работы с ChromaDB индексом."""

import logging
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class FAISSIndex:
    """
    Обёртка над ChromaDB для хранения и поиска векторов.

    Использует косинусное сходство для поиска релевантных документов.
    """

    def __init__(self, dimension: int = 1024):
        """
        Инициализирует ChromaDB клиент.

        Args:
            dimension: Размерность векторов эмбеддингов (игнорируется в ChromaDB)
        """
        self.dimension = dimension
        # Создаём in-memory клиент
        self.client = chromadb.Client(Settings(
            anonymized_telemetry=False,
            allow_reset=True
        ))
        # Создаём коллекцию
        self.collection = self.client.create_collection(
            name="cities",
            metadata={"hnsw:space": "cosine"}  # Косинусное сходство
        )
        logger.info(f"Создан ChromaDB индекс, размерность: {dimension}")

    def add_documents(
        self,
        embeddings: List[List[float]],
        documents: List[Dict[str, str]]
    ):
        """
        Добавляет документы в индекс.

        Args:
            embeddings: Список векторов эмбеддингов
            documents: Список метаданных документов
        """
        if len(embeddings) != len(documents):
            raise ValueError(
                f"Количество эмбеддингов ({len(embeddings)}) не совпадает "
                f"с количеством документов ({len(documents)})"
            )

        # Конвертируем numpy array в list если нужно
        if hasattr(embeddings, 'tolist'):
            embeddings = embeddings.tolist()

        # Создаём ID для документов
        ids = [f"doc_{i}" for i in range(len(documents))]

        # Извлекаем тексты и метаданные
        texts = [doc["text"] for doc in documents]
        metadatas = [
            {"city": doc["city"], "source": doc.get("source", "")}
            for doc in documents
        ]

        # Добавляем в ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )

        logger.info(f"Добавлено {len(documents)} документов в индекс. "
                   f"Всего: {self.collection.count()}")

    def search(
        self,
        query_embedding: List[float],
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Ищет наиболее релевантные документы.

        Args:
            query_embedding: Вектор запроса
            k: Количество результатов

        Returns:
            Список результатов с метаданными и score
        """
        total = self.collection.count()
        if total == 0:
            logger.warning("Индекс пуст, возвращаю пустой результат")
            return []

        # Конвертируем numpy array в list если нужно
        if hasattr(query_embedding, 'tolist'):
            query_embedding = query_embedding.tolist()

        # Ограничиваем k размером коллекции
        k = min(k, total)

        # Поиск
        results_data = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k
        )

        # Форматируем результаты
        results = []
        if results_data["ids"]:
            for i in range(len(results_data["ids"][0])):
                metadata = results_data["metadatas"][0][i]
                text = results_data["documents"][0][i]
                distance = results_data["distances"][0][i]

                # ChromaDB возвращает расстояние, конвертируем в similarity score
                # Для косинусного расстояния: similarity = 1 - distance
                score = 1.0 - distance

                results.append({
                    "city": metadata.get("city", "Unknown"),
                    "text": text,
                    "source": metadata.get("source", ""),
                    "score": float(score)
                })

        logger.info(f"Найдено {len(results)} результатов")
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику индекса."""
        return {
            "total_documents": self.collection.count(),
            "dimension": self.dimension,
            "index_type": "ChromaDB (cosine)",
        }
