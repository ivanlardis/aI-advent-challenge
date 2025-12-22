"""Модуль для генерации эмбеддингов через sentence-transformers."""

import logging
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """
    Обёртка над sentence-transformers для генерации эмбеддингов.

    Использует модель intfloat/multilingual-e5-large с поддержкой
    инструкций query:/passage: для улучшения качества поиска.
    """

    def __init__(self, model_name: str = "intfloat/multilingual-e5-large"):
        """
        Инициализирует модель эмбеддингов.

        Args:
            model_name: Название модели из HuggingFace Hub.
                       По умолчанию: intfloat/multilingual-e5-large (~2 ГБ)
                       Альтернатива: paraphrase-multilingual-MiniLM-L12-v2 (420 МБ)
        """
        logger.info(f"Загружаю модель эмбеддингов: {model_name}")
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        logger.info(f"Модель загружена, размерность: {self.get_dimension()}")

    def get_dimension(self) -> int:
        """Возвращает размерность векторов эмбеддингов."""
        return self.model.get_sentence_embedding_dimension()

    def encode_documents(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress_bar: bool = False
    ) -> np.ndarray:
        """
        Кодирует документы в векторы эмбеддингов.

        Для моделей E5 автоматически добавляет префикс "passage:"
        для улучшения качества поиска.

        Args:
            texts: Текст или список текстов для кодирования
            batch_size: Размер батча для обработки
            show_progress_bar: Показывать прогресс-бар

        Returns:
            Нормализованные векторы эмбеддингов (N x D)
        """
        if isinstance(texts, str):
            texts = [texts]

        # E5 модели требуют префикс "passage:" для документов
        if "e5" in self.model_name.lower():
            texts = [f"passage: {text}" for text in texts]

        logger.info(f"Генерирую эмбеддинги для {len(texts)} документов")

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress_bar,
            normalize_embeddings=True  # Нормализация для использования с IndexFlatIP
        )

        return embeddings

    def encode_query(self, query: str) -> np.ndarray:
        """
        Кодирует поисковый запрос в вектор эмбеддинга.

        Для моделей E5 автоматически добавляет префикс "query:"
        для улучшения качества поиска.

        Args:
            query: Текст запроса

        Returns:
            Нормализованный вектор эмбеддинга (1 x D)
        """
        # E5 модели требуют префикс "query:" для запросов
        if "e5" in self.model_name.lower():
            query = f"query: {query}"

        embedding = self.model.encode(
            query,
            normalize_embeddings=True
        )

        return embedding
