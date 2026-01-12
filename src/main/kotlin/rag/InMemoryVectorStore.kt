package rag

import parser.Document

/**
 * In-memory хранилище для документов и их векторов
 */
class InMemoryVectorStore(private val vectorizer: TfIdfVectorizer) {
    private val documents = mutableListOf<Document>()
    private val vectors = mutableListOf<Map<String, Double>>()

    /**
     * Добавить документ и его вектор в хранилище
     */
    fun addDocument(doc: Document, vector: Map<String, Double>) {
        documents.add(doc)
        vectors.add(vector)
    }

    /**
     * Поиск релевантных документов по query вектору
     */
    fun search(queryVector: Map<String, Double>, topK: Int, minSimilarity: Double = 0.0): List<SearchResult> {
        if (documents.isEmpty()) return emptyList()

        val results = documents.indices.map { idx ->
            val doc = documents[idx]
            val vec = vectors[idx]
            val similarity = vectorizer.cosineSimilarity(queryVector, vec)

            SearchResult(doc, similarity)
        }

        return results
            .filter { it.score >= minSimilarity }
            .sortedByDescending { it.score }
            .take(topK)
    }

    /**
     * Очистить хранилище
     */
    fun clear() {
        documents.clear()
        vectors.clear()
    }

    /**
     * Получить размер хранилища
     */
    fun size(): Int = documents.size

    /**
     * Получить все документы
     */
    fun getAllDocuments(): List<Document> = documents.toList()
}
