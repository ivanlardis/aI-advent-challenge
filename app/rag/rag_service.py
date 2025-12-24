"""Главный сервис RAG для работы со справочником городов."""

import logging
from typing import List, Dict, Any, Optional

from app.rag.parser import parse_cities_file, deduplicate_cities
from app.rag.embeddings import EmbeddingModel
from app.rag.index import FAISSIndex

logger = logging.getLogger(__name__)


class CityRAG:
    """
    Главный класс RAG-системы для справочника городов России.

    Объединяет парсинг, генерацию эмбеддингов и поиск в ChromaDB индексе.
    """

    def __init__(
        self,
        data_file: str = "rag_example_cities_ru.txt",
        index_dir: str = "data/faiss_index",  # Игнорируется для ChromaDB in-memory
        model_name: str = "intfloat/multilingual-e5-large",
        deduplicate: bool = True
    ):
        """
        Инициализирует RAG-систему.

        Args:
            data_file: Путь к файлу с данными о городах
            index_dir: Игнорируется (ChromaDB in-memory)
            model_name: Название модели эмбеддингов
            deduplicate: Дедуплицировать города при индексации
        """
        self.data_file = data_file
        self.index_dir = index_dir
        self.model_name = model_name
        self.deduplicate = deduplicate

        self.embedding_model: Optional[EmbeddingModel] = None
        self.index: Optional[FAISSIndex] = None

    async def initialize(self):
        """
        Инициализирует индекс.

        Создаёт новый ChromaDB индекс в памяти и заполняет его данными.
        """
        # Инициализируем модель эмбеддингов
        logger.info("Инициализация модели эмбеддингов...")
        self.embedding_model = EmbeddingModel(self.model_name)

        # Всегда создаём новый индекс (ChromaDB in-memory)
        logger.info("Создание ChromaDB индекса...")
        await self._build_index()
        logger.info(f"Индекс создан: {self.index.get_stats()}")

    async def _build_index(self):
        """Строит индекс с нуля из исходного файла."""
        logger.info(f"Парсинг файла: {self.data_file}")
        documents = parse_cities_file(self.data_file)

        if self.deduplicate:
            logger.info("Дедупликация городов...")
            documents = deduplicate_cities(documents)

        logger.info(f"Генерация эмбеддингов для {len(documents)} документов...")
        texts = [doc["text"] for doc in documents]
        embeddings = self.embedding_model.encode_documents(
            texts,
            batch_size=32,
            show_progress_bar=True
        )

        logger.info("Создание ChromaDB индекса...")
        self.index = FAISSIndex(dimension=self.embedding_model.get_dimension())
        self.index.add_documents(embeddings, documents)

    def search(
        self,
        query: str,
        k: int = 5,
        min_score: Optional[float] = None,
        apply_filter: bool = True
    ) -> Dict[str, Any]:
        """
        Поиск релевантных документов с опциональной фильтрацией по score.

        Args:
            query: Текст запроса
            k: Количество результатов (до фильтрации)
            min_score: Минимальный порог релевантности (0.0-1.0)
            apply_filter: Применять ли фильтрацию по порогу

        Returns:
            Словарь с метаданными фильтрации:
            - all_results: все результаты до фильтрации
            - filtered_results: результаты после фильтрации
            - filtered_count: количество отфильтрованных документов
            - filter_applied: был ли применен фильтр
            - min_score_used: использованный порог
        """
        if self.index is None or self.embedding_model is None:
            raise RuntimeError("RAG не инициализирован. Вызовите initialize() сначала.")

        logger.info(
            f"RAG Query: '{query[:50]}' | k={k} | "
            f"min_score={min_score} | filter={apply_filter}"
        )

        # Получаем результаты от индекса
        query_embedding = self.embedding_model.encode_query(query)
        all_results = self.index.search(query_embedding, k)

        # Логируем все результаты
        for i, result in enumerate(all_results, 1):
            logger.info(
                f"Result {i}: {result['city']} | "
                f"score={result['score']:.3f} | "
                f"text_len={len(result['text'])}"
            )

        # Применяем фильтрацию если нужно
        filtered_results = all_results
        if apply_filter and min_score is not None:
            filtered_results = [r for r in all_results if r["score"] >= min_score]
            rejected = [r for r in all_results if r["score"] < min_score]

            logger.info(
                f"Filtering: {len(all_results)} → {len(filtered_results)} results | "
                f"rejected={len(rejected)}"
            )

            for r in rejected:
                logger.debug(
                    f"Rejected: {r['city']} (score={r['score']:.3f} < {min_score})"
                )

        return {
            "all_results": all_results,
            "filtered_results": filtered_results,
            "filtered_count": len(all_results) - len(filtered_results),
            "filter_applied": apply_filter and min_score is not None,
            "min_score_used": min_score
        }

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику RAG-системы."""
        if self.index is None:
            return {"status": "not_initialized"}

        stats = self.index.get_stats()
        stats.update({
            "model_name": self.model_name,
            "data_file": self.data_file,
        })
        return stats
