package rag

import parser.Document

/**
 * Результат поиска с similarity score
 */
data class SearchResult(
    val document: Document,
    val score: Double
)
