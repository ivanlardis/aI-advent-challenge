"""RAG модуль для работы со справочником городов России."""

from app.rag.parser import parse_cities_file
from app.rag.embeddings import EmbeddingModel
from app.rag.index import FAISSIndex
from app.rag.rag_service import CityRAG

__all__ = [
    "parse_cities_file",
    "EmbeddingModel",
    "FAISSIndex",
    "CityRAG",
]
